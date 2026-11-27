#!/usr/bin/env python3

import pickle
import re
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

from app import models


class Command(BaseCommand):
    help = "Populate metacell-type similarity scores and gene pairs."

    def find_mapping_files(self, data_dir):
        return sorted(Path(data_dir).glob("*_mapping.tsv.gz"))

    def parse_mapping_name(self, path):
        match = re.match(r"^(.+)-(.+)_mapping\.tsv\.gz$", path.name)
        return (match.group(1), match.group(2)) if match else (None, None)

    def find_gene_pair_file(self, data_dir, species1, species2):
        data_dir = Path(data_dir)
        paths = [
            data_dir / f"{species1}-{species2}.gene_pairs.pkl",
            data_dir / f"{species2}-{species1}.gene_pairs.pkl",
        ]
        return next((path for path in paths if path.exists()), None)

    def get_dataset(self, internal_id):
        return models.Dataset.objects.filter(internal_id=internal_id).first()

    def get_metacell_types(self, dataset):
        return list(models.MetacellType.objects.filter(dataset=dataset).order_by("name"))

    def normalize_db_cell_type(self, name):
        name = str(name).strip()
        name = re.sub(r"[_\s]+", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip().lower()

    def normalize_samap_cell_type(self, name):
        name = str(name).strip()

        if "_" in name:
            name = name.split("_", 1)[1]

        name = re.sub(r"[_\s]+", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip().lower()

    def build_type_lookup(self, metacell_types):
        lookup = {}

        for metacell_type in metacell_types:
            key = self.normalize_db_cell_type(metacell_type.name)
            lookup.setdefault(key, []).append(metacell_type)

        return lookup

    def match_cell_type(self, name, lookup):
        key = self.normalize_samap_cell_type(name)
        matches = lookup.get(key, [])

        if len(matches) == 1:
            return matches[0]

        compact = re.sub(r"[^a-z0-9]", "", key)

        matches = [
            value
            for lookup_key, values in lookup.items()
            if re.sub(r"[^a-z0-9]", "", lookup_key) == compact
            for value in values
        ]

        return matches[0] if len(matches) == 1 else None

    def read_mapping(self, path):
        df = pd.read_csv(path, sep="\t", compression="gzip")

        required = {"index", "variable", "value"}
        missing = required - set(df.columns)

        if missing:
            raise ValueError(
                f"{path.name} missing columns: {', '.join(sorted(missing))}"
            )

        df["index"] = df["index"].astype(str).str.strip()
        df["variable"] = df["variable"].astype(str).str.strip()
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        return df.dropna(subset=["value"])

    def read_gene_pairs(self, path):
        if path is None:
            return {}

        with open(path, "rb") as handle:
            data = pickle.load(handle)

        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(data)

        result = {}

        for column in df.columns:
            column = str(column)

            if "_pval1" in column or "_pval2" in column or ";" not in column:
                continue

            left_type, right_type = column.split(";", 1)
            pairs = []

            for value in df[column].dropna():
                if not isinstance(value, str) or ";" not in value:
                    continue

                gene1, gene2 = value.split(";", 1)
                gene1 = gene1.strip()
                gene2 = gene2.strip()

                if gene1 and gene2:
                    pairs.append([gene1, gene2])

            if not pairs:
                continue

            key = (
                self.normalize_samap_cell_type(left_type),
                self.normalize_samap_cell_type(right_type),
            )

            result[key] = pairs

        return result

    def gene_pair_key(self, source, target):
        return (
            self.normalize_samap_cell_type(source),
            self.normalize_samap_cell_type(target),
        )

    def strip_samap_prefix(self, gene_name):
        gene_name = str(gene_name).strip()

        if "_" not in gene_name:
            return gene_name

        return gene_name.split("_", 1)[1]

    def get_gene(self, dataset, samap_gene_name, cache):
        samap_gene_name = str(samap_gene_name).strip()
        key = (dataset.pk, samap_gene_name)

        if key in cache:
            return cache[key]

        db_gene_name = self.strip_samap_prefix(samap_gene_name)

        gene = models.Gene.objects.filter(species=dataset.species, name=db_gene_name).first()
        if gene is None:
            print(f"    [GENE NOT FOUND IN DB] SAMAP={samap_gene_name} | DB={db_gene_name}")

        cache[key] = gene
        return gene

    def convert_gene_pairs(self, pairs, dataset1, dataset2, cache):
        result = []

        for gene1_name, gene2_name in pairs:
            gene1 = self.get_gene(
                dataset1,
                gene1_name,
                cache,
            )

            gene2 = self.get_gene(
                dataset2,
                gene2_name,
                cache,
            )

            if gene1 is None or gene2 is None:
                continue

            result.append([
                gene1.pk,
                gene2.pk,
            ])

        return result

    def find_similarity(self, mt1, mt2):
        return models.MetacellTypeSimilarity.objects.filter(
            metacelltype=mt1,
            metacelltype2=mt2,
        ).first() or models.MetacellTypeSimilarity.objects.filter(
            metacelltype=mt2,
            metacelltype2=mt1,
        ).first()

    def save_similarity(self, mt1, mt2, score, gene_pairs):
        existing = self.find_similarity(mt1, mt2)

        if existing is None:
            models.MetacellTypeSimilarity.objects.create(
                metacelltype=mt1,
                metacelltype2=mt2,
                samap_score=score,
                samap_gene_pairs=gene_pairs or None,
            )
            return "created"

        existing.samap_score = score
        existing.samap_gene_pairs = gene_pairs or None
        existing.save(update_fields=["samap_score", "samap_gene_pairs"])

        return "updated"

    def populate_mapping(self, data_dir, mapping_path):
        species1, species2 = self.parse_mapping_name(mapping_path)

        if not species1 or not species2:
            print(f"[SKIP] {mapping_path.name}: invalid filename")
            return

        dataset1 = self.get_dataset(species1)
        dataset2 = self.get_dataset(species2)

        if dataset1 is None or dataset2 is None:
            print(f"[SKIP] {mapping_path.name}: dataset missing")
            return

        types1 = self.get_metacell_types(dataset1)
        types2 = self.get_metacell_types(dataset2)

        lookup1 = self.build_type_lookup(types1)
        lookup2 = self.build_type_lookup(types2)

        print(f"[LOAD] {mapping_path.name}")

        mapping_df = self.read_mapping(mapping_path)

        gene_pair_path = self.find_gene_pair_file(
            data_dir,
            species1,
            species2,
        )

        if gene_pair_path:
            print(f"  Reading gene pairs: {gene_pair_path.name}")
            gene_pairs = self.read_gene_pairs(gene_pair_path)
        else:
            print("  No gene-pair file found")
            gene_pairs = {}

        gene_cache = {}
        created = 0
        updated = 0
        skipped = 0

        for row in mapping_df.itertuples(index=False):
            source_name = str(row.index).strip()
            target_name = str(row.variable).strip()
            score = float(row.value)

            mt1 = self.match_cell_type(
                source_name,
                lookup1,
            )

            mt2 = self.match_cell_type(
                target_name,
                lookup2,
            )

            if mt1 is None or mt2 is None:
                skipped += 1
                continue

            pair_key = self.gene_pair_key(
                source_name,
                target_name,
            )

            pairs = gene_pairs.get(pair_key, [])

            if not pairs:
                reverse_key = (
                    pair_key[1],
                    pair_key[0],
                )

                reverse_pairs = gene_pairs.get(reverse_key, [])

                pairs = [
                    [gene2, gene1]
                    for gene1, gene2 in reverse_pairs
                ]

            gene_pair_ids = self.convert_gene_pairs(
                pairs,
                dataset1,
                dataset2,
                gene_cache,
            )

            result = self.save_similarity(
                mt1,
                mt2,
                score,
                gene_pair_ids,
            )

            if result == "created":
                created += 1
            else:
                updated += 1

        print(f"  Similarities created: {created:,}")
        print(f"  Similarities updated: {updated:,}")
        print(f"  Rows skipped: {skipped:,}")

    def populate(self, data_dir):
        mapping_files = self.find_mapping_files(data_dir)
        print(f"Found {len(mapping_files)} SAMAP mapping files.")

        for mapping_path in mapping_files:
            try:
                self.populate_mapping(data_dir, mapping_path)
            except Exception as exc:
                print(f"[ERROR] {mapping_path.name}: {exc}")
                raise

    def add_arguments(self, parser):
        parser.add_argument(
            "data_dir",
            help="Directory containing SAMAP result files.",
        )

    def handle(self, *args, **options):
        self.populate(options["data_dir"])
