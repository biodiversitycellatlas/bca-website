#!/usr/bin/env python3

import csv
import gzip
import re
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

from app import models


class Command(BaseCommand):
    help = "Populate gene modules, membership scores, and module eigengene values."

    def open_text(self, path):
        path = str(path)
        return gzip.open(path, "rt") if path.endswith(".gz") else open(path, "r")

    def find_datasets(self, data_dir):
        data_dir = Path(data_dir)
        pattern = re.compile(r"^(.+)\.gene_membership\.tsv(?:\.gz)?$")
        return sorted(
            match.group(1)
            for path in data_dir.glob("*.gene_membership.tsv*")
            if (match := pattern.match(path.name))
        )

    def get_files(self, data_dir, internal_id):
        data_dir = Path(data_dir)
        return {
            "membership": data_dir / f"{internal_id}.gene_membership.tsv.gz",
            "modules": data_dir / f"{internal_id}.gene_modules.tsv.gz",
            "eigengenes": data_dir / f"{internal_id}.module_eigengenes.tsv.gz",
        }

    def check_files(self, files):
        return [files[key].name for key in files if not files[key].exists()]

    def get_dataset(self, internal_id):
        return models.Dataset.objects.filter(internal_id=internal_id).first()

    def has_gene_modules(self, dataset):
        return models.GeneModule.objects.filter(dataset=dataset).exists()

    def read_modules(self, path):
        with self.open_text(path) as handle:
            reader = csv.reader(handle, delimiter="\t")
            rows = list(reader)

        if not rows:
            raise ValueError(f"{path.name} is empty")

        header = [str(x).strip() for x in rows[0]]

        try:
            gene_idx = next(i for i, x in enumerate(header) if x.lower() == "gene")
            module_idx = next(i for i, x in enumerate(header) if x.lower() == "module")
        except StopIteration:
            raise ValueError(f"{path.name} must contain 'gene' and 'module' columns")

        records = []

        for row in rows[1:]:
            if len(row) <= max(gene_idx, module_idx):
                continue

            gene = str(row[gene_idx]).strip()
            module = str(row[module_idx]).strip()

            if not gene or not module:
                continue

            records.append((gene, module))

        if not records:
            raise ValueError(f"{path.name} contains no valid gene/module rows")

        df = pd.DataFrame(records, columns=["gene", "module"])
        df["gene"] = df["gene"].astype(str).str.strip()
        df["module"] = df["module"].astype(str).str.strip()

        return df.drop_duplicates(subset=["gene"])

    def _split_matrix_line(self, line):
        line = line.rstrip("\r\n")

        if not line.strip():
            return None

        parts = line.split("\t")

        if len(parts) > 1:
            return [x.strip() for x in parts]

        return re.split(r"\s+", line.strip())

    def _parse_matrix(self, path):
        with self.open_text(path) as handle:
            lines = [line for line in handle if line.strip()]

        if not lines:
            raise ValueError(f"{path.name} is empty")

        header = self._split_matrix_line(lines[0])

        if not header or len(header) < 2:
            raise ValueError(f"{path.name} must contain an identifier and at least one value column")

        header = [str(x).strip() for x in header]

        records = []
        expected = len(header)

        for line in lines[1:]:
            parts = self._split_matrix_line(line)

            if not parts:
                continue

            if len(parts) == expected:
                identifier = str(parts[0]).strip()
                values = parts[1:]
            elif len(parts) > expected:
                identifier = str(parts[0]).strip()
                values = parts[-(expected - 1):]
            else:
                continue

            if not identifier:
                continue

            numeric = pd.to_numeric(pd.Series(values), errors="coerce")

            if not pd.notna(numeric).any():
                continue

            values = numeric.tolist()
            records.append([identifier, *values])

        if not records:
            raise ValueError(f"{path.name} contains no valid matrix rows")

        columns = [header[0], *header[1:]]
        df = pd.DataFrame(records, columns=columns)

        df[columns[0]] = df[columns[0]].astype(str).str.strip()
        df = df.set_index(columns[0])
        df = df.apply(pd.to_numeric, errors="coerce")

        df = df.loc[:, df.notna().any(axis=0)]
        df = df.loc[df.notna().any(axis=1)]

        if df.empty or df.shape[1] == 0:
            raise ValueError(f"{path.name} contains no numeric matrix data")

        return df

    def read_matrix(self, path):
        return self._parse_matrix(path)

    def get_genes(self, dataset):
        return {
            gene.name: gene
            for gene in models.Gene.objects.filter(species=dataset.species)
        }

    def get_metacells(self, dataset):
        return {
            metacell.name: metacell
            for metacell in models.Metacell.objects.filter(dataset=dataset)
        }

    def get_or_create_modules(self, dataset, module_names):
        modules = {}

        for module_name in sorted(module_names):
            module_name = str(module_name).strip()

            if not module_name:
                continue

            module, created = models.GeneModule.objects.get_or_create(
                dataset=dataset,
                name=module_name,
            )
            modules[module_name] = module

            if created:
                print(f"  Created module: {module_name}")

        return modules

    def build_memberships(self, dataset, modules_df, membership_df, modules):
        genes = self.get_genes(dataset)
        objects = []
        missing_genes = 0
        missing_scores = 0

        for row in modules_df.itertuples(index=False):
            gene_name = str(row.gene).strip()
            module_name = str(row.module).strip()

            gene = genes.get(gene_name)

            if gene is None:
                missing_genes += 1
                continue

            if gene_name not in membership_df.index:
                missing_scores += 1
                continue

            column = f"kME{module_name}"

            if column not in membership_df.columns:
                raise ValueError(f"{column} not found in gene membership matrix")

            score = membership_df.at[gene_name, column]

            if isinstance(score, pd.Series):
                score = score.iloc[0]

            if pd.isna(score):
                continue

            objects.append(
                models.GeneModuleMembership(
                    module=modules[module_name],
                    gene=gene,
                    membership_score=float(score),
                )
            )

        print(f"  Memberships matched: {len(objects):,}")
        print(f"  Genes missing from database: {missing_genes:,}")
        print(f"  Genes missing from membership matrix: {missing_scores:,}")

        return objects

    def build_eigengenes(self, dataset, eigengene_df, modules):
        metacells = self.get_metacells(dataset)
        objects = []
        missing_metacells = 0

        for metacell_name, row in eigengene_df.iterrows():
            metacell = metacells.get(str(metacell_name).strip())

            if metacell is None:
                missing_metacells += 1
                continue

            for module_name, value in row.items():
                module_name = str(module_name).strip()

                if module_name not in modules or pd.isna(value):
                    continue

                objects.append(
                    models.GeneModuleEigengene(
                        module=modules[module_name],
                        metacell=metacell,
                        eigengene_value=float(value),
                    )
                )

        print(f"  Eigengene values matched: {len(objects):,}")
        print(f"  Metacells missing from database: {missing_metacells:,}")

        return objects

    def save_memberships(self, objects):
        if not objects:
            return 0

        keys = {(obj.gene_id, obj.module_id) for obj in objects}
        gene_ids = {gene_id for gene_id, _ in keys}
        module_ids = {module_id for _, module_id in keys}

        existing = {
            (obj.gene_id, obj.module_id): obj
            for obj in models.GeneModuleMembership.objects.filter(
                gene_id__in=gene_ids,
                module_id__in=module_ids,
            )
        }

        to_create = []
        to_update = []

        for obj in objects:
            existing_obj = existing.get((obj.gene_id, obj.module_id))

            if existing_obj is None:
                to_create.append(obj)
            else:
                existing_obj.membership_score = obj.membership_score
                to_update.append(existing_obj)

        if to_create:
            models.GeneModuleMembership.objects.bulk_create(
                to_create,
                batch_size=10000,
            )

        if to_update:
            models.GeneModuleMembership.objects.bulk_update(
                to_update,
                ["membership_score"],
                batch_size=10000,
            )

        return len(to_create) + len(to_update)

    def save_eigengenes(self, objects):
        if not objects:
            return 0

        keys = {(obj.metacell_id, obj.module_id) for obj in objects}
        metacell_ids = {metacell_id for metacell_id, _ in keys}
        module_ids = {module_id for _, module_id in keys}

        existing = {
            (obj.metacell_id, obj.module_id): obj
            for obj in models.GeneModuleEigengene.objects.filter(
                metacell_id__in=metacell_ids,
                module_id__in=module_ids,
            )
        }

        to_create = []
        to_update = []

        for obj in objects:
            existing_obj = existing.get((obj.metacell_id, obj.module_id))

            if existing_obj is None:
                to_create.append(obj)
            else:
                existing_obj.eigengene_value = obj.eigengene_value
                to_update.append(existing_obj)

        if to_create:
            models.GeneModuleEigengene.objects.bulk_create(
                to_create,
                batch_size=10000,
            )

        if to_update:
            models.GeneModuleEigengene.objects.bulk_update(
                to_update,
                ["eigengene_value"],
                batch_size=10000,
            )

        return len(to_create) + len(to_update)

    def populate_dataset(self, data_dir, internal_id):
        files = self.get_files(data_dir, internal_id)
        missing = self.check_files(files)

        if missing:
            print(f"[SKIP] {internal_id}: missing {', '.join(missing)}")
            return

        dataset = self.get_dataset(internal_id)

        if dataset is None:
            print(f"[SKIP] {internal_id}: dataset does not exist in database")
            return

        if self.has_gene_modules(dataset):
            print(f"[SKIP] {internal_id}: gene modules already exist")
            return

        print(f"[LOAD] {internal_id}")

        print("  Reading gene modules...")
        modules_df = self.read_modules(files["modules"])
        print(f"  Gene-module assignments: {len(modules_df):,}")

        print("  Reading gene membership...")
        membership_df = self.read_matrix(files["membership"])
        print(
            f"  Membership matrix: {membership_df.shape[0]:,} genes x "
            f"{membership_df.shape[1]:,} modules"
        )

        print("  Reading module eigengenes...")
        eigengene_df = self.read_matrix(files["eigengenes"])
        print(
            f"  Eigengene matrix: {eigengene_df.shape[0]:,} metacells x "
            f"{eigengene_df.shape[1]:,} modules"
        )

        membership_modules = {
            column.removeprefix("kME")
            for column in membership_df.columns
            if column.startswith("kME")
        }

        assignment_modules = set(modules_df["module"].astype(str).str.strip())
        eigengene_modules = set(eigengene_df.columns.astype(str).str.strip())

        module_names = assignment_modules | membership_modules | eigengene_modules

        modules = self.get_or_create_modules(dataset, module_names)

        print("  Building gene-module memberships...")
        memberships = self.build_memberships(
            dataset,
            modules_df,
            membership_df,
            modules,
        )

        print("  Building module eigengenes...")
        eigengenes = self.build_eigengenes(
            dataset,
            eigengene_df,
            modules,
        )

        print("  Saving gene-module memberships...")
        saved_memberships = self.save_memberships(memberships)
        print(f"  Saved memberships: {saved_memberships:,}")

        print("  Saving module eigengenes...")
        saved_eigengenes = self.save_eigengenes(eigengenes)
        print(f"  Saved eigengenes: {saved_eigengenes:,}")

        print(f"[DONE] {internal_id}")

    def populate(self, data_dir):
        datasets = self.find_datasets(data_dir)
        print(f"Found {len(datasets)} datasets.")

        for internal_id in datasets:
            try:
                self.populate_dataset(data_dir, internal_id)
            except Exception as exc:
                print(f"[ERROR] {internal_id}: {exc}")
                raise

    def add_arguments(self, parser):
        parser.add_argument("data_dir", help="Directory containing gene module files.")

    def handle(self, *args, **options):
        self.populate(options["data_dir"])
