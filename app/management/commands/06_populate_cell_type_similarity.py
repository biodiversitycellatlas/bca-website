import pickle
import re
from collections import defaultdict
from pathlib import Path
import pandas as pd
import numpy as np
from rds2py import read_rds

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.core.management.color import color_style

from app import models


style = color_style()

class CellTypeSimilarity:
    def __init__(self):
        self.datasets = {}
        self.metacell_types = {}
        self.genes = {}
        self.existing_pairs = {}
        self.prefixes = []

    def get_dataset(self, name):
        if name not in self.datasets:
            try:
                self.datasets[name] = models.Dataset.objects.select_related("species").get(internal_id=name)
                # Append prefix
                self.prefixes.append(name[:6])
            except models.Dataset.DoesNotExist as exc:
                raise CommandError(f"Dataset {name!r} not found") from exc
        return self.datasets[name]

    def get_metacell_types(self, dataset):
        if dataset.id not in self.metacell_types:
            self.metacell_types[dataset.id] = list(models.MetacellType.objects.filter(dataset=dataset).only("id", "name"))
        return self.metacell_types[dataset.id]

    @staticmethod
    def normalize_db_cell_type(name):
        return re.sub(r"[_\s]+", " ", str(name)).strip().lower()

    def normalize_cell_type(self, name):
        for prefix in self.prefixes:
            prefix = f"{prefix}_"
            if str(name).startswith(prefix):
                name = str(name)[len(prefix):]
                break
        return re.sub(r"[_\s]+", " ", name).strip().lower()

    def build_type_lookup(self, dataset, normalizer=None):
        normalizer = normalizer or self.normalize_db_cell_type
        return {normalizer(mt.name): mt for mt in self.get_metacell_types(dataset)}

    def preload_genes(self, dataset):
        genes = dict(dataset.species.genes.values_list("name", "id"))
        self.genes[dataset.id] = genes
        return genes

    def get_gene(self, dataset, gene_name, strip_prefix=False):
        gene_name = str(gene_name)
        if strip_prefix:
            gene_name = gene_name.split("_", 1)[-1]
        self.preload_genes(dataset)
        return self.genes[dataset.id].get(gene_name)

    def pair_has_score(self, dataset1, dataset2, score_field):
        key = (dataset1.id, dataset2.id, score_field)
        if key not in self.existing_pairs:
            self.existing_pairs[key] = models.MetacellTypeSimilarity.objects.filter(
                metacelltype__dataset_id=dataset1.id,
                metacelltype2__dataset_id=dataset2.id,
                **{f"{score_field}__isnull": False},
            ).exists()
        return self.existing_pairs[key]

    @staticmethod
    def bulk_insert(objects):
        if objects:
            models.MetacellTypeSimilarity.objects.bulk_create(objects, batch_size=5000)

    def bulk_upsert(self, objects, score_field, gene_pairs_field):
        if not objects:
            return

        table = models.MetacellTypeSimilarity._meta.db_table
        sql = f"""
            INSERT INTO {table} (
                metacelltype_id,
                metacelltype2_id,
                {score_field},
                {gene_pairs_field}
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (metacelltype_id, metacelltype2_id)
            DO UPDATE SET
                {score_field} = EXCLUDED.{score_field},
                {gene_pairs_field} = EXCLUDED.{gene_pairs_field}
        """

        with connection.cursor() as cursor:
            cursor.executemany(sql, objects)


class SAMap(CellTypeSimilarity):
    def find_mapping_files(self, data_dir):
        return sorted(data_dir.glob("*_mapping.tsv.gz"))

    @staticmethod
    def parse_mapping_name(mapping_file):
        name = mapping_file.name.removesuffix("_mapping.tsv.gz")
        try:
            species1, species2 = name.split("-", 1)
        except ValueError as exc:
            raise CommandError(f"Invalid SAMAP mapping filename: {mapping_file.name}") from exc
        return species1, species2

    @staticmethod
    def find_gene_pair_file(mapping_file):
        base = mapping_file.name.removesuffix("_mapping.tsv.gz")
        species1, species2 = base.split("-", 1)
        for name in (f"{species1}-{species2}.gene_pairs.pkl", f"{species2}-{species1}.gene_pairs.pkl"):
            path = mapping_file.with_name(name)
            if path.exists():
                return path
        return None

    @staticmethod
    def read_mapping(mapping_file):
        return pd.read_csv(mapping_file, sep="\t", compression="gzip")

    @staticmethod
    def read_gene_pairs(gene_pair_file):
        with gene_pair_file.open("rb") as handle:
            data = pickle.load(handle)
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        columns = [column for column in df.columns if not str(column).endswith(("_pval1", "_pval2"))]

        pairs_by_column = {}
        for column in columns:
            values = df[column].dropna()
            if values.empty:
                continue

            pairs = []
            for value in values:
                parts = str(value).split(";")
                if len(parts) == 2:
                    pairs.append((parts[0], parts[1]))

            if pairs:
                pairs_by_column[column] = pairs

        return pairs_by_column

    def convert_gene_pairs(self, gene_pairs, dataset1, dataset2):
        genes1 = self.preload_genes(dataset1)
        genes2 = self.preload_genes(dataset2)

        converted = {}

        for column, pairs in gene_pairs.items():
            converted[column] = []

            for gene1, gene2 in pairs:
                gene1 = genes1.get(str(gene1).split("_", 1)[-1])
                gene2 = genes2.get(str(gene2).split("_", 1)[-1])

                if gene1 and gene2:
                    converted[column].append([gene1, gene2])

        return converted

    def populate_mapping(self, mapping_file):
        species1, species2 = self.parse_mapping_name(mapping_file)
        print(f"[SAMAP] Processing {species1} -> {species2}: {mapping_file.name}", flush=True)

        dataset1 = self.get_dataset(species1)
        dataset2 = self.get_dataset(species2)

        if self.pair_has_score(dataset1, dataset2, "samap_score"):
            print(style.WARNING(f"[SAMAP] Skipping {species1} -> {species2}: SAMap scores already exist"), flush=True)
            return

        lookup1 = self.build_type_lookup(dataset1, self.normalize_cell_type)
        lookup2 = self.build_type_lookup(dataset2, self.normalize_cell_type)

        gene_pair_file = self.find_gene_pair_file(mapping_file)
        if gene_pair_file is None:
            raise CommandError(f"No gene-pair file found for {mapping_file}")

        gene_pairs = self.convert_gene_pairs(self.read_gene_pairs(gene_pair_file), dataset1, dataset2)
        df = self.read_mapping(mapping_file)

        if not {"index", "variable", "value"}.issubset(df.columns):
            raise CommandError(f"Unexpected columns in {mapping_file}: {list(df.columns)}")

        similarities = []
        skipped_elems = []
        skipped = 0

        for index, variable, value in df[["index", "variable", "value"]].itertuples(index=False, name=None):
            mt1 = lookup1.get(self.normalize_cell_type(index))
            mt2 = lookup2.get(self.normalize_cell_type(variable))
            if mt1 is None or mt2 is None:
                if mt1 is None:
                    skipped_elems.append(index)
                if mt2 is None:
                    skipped_elems.append(variable)
                skipped += 1
                continue

            pairs = gene_pairs.get(f"{index};{variable}")
            similarities.append((mt1.id, mt2.id, value, pairs))

        self.bulk_upsert(similarities, "samap_score", "samap_gene_pairs")
        print(style.SUCCESS(f"[SAMAP] Finished {mapping_file.name}: {len(similarities):,} inserted, {skipped:,} skipped"),
        flush=True)

        if skipped > 0:
            print(style.WARNING(f"Skipped elements: {', '.join(map(str, set(skipped_elems)))}"))

    def run(self, data_dir):
        mapping_files = self.find_mapping_files(data_dir)
        print(f"[SAMAP] Found {len(mapping_files):,} mapping files", flush=True)
        for mapping_file in mapping_files:
            with transaction.atomic():
                self.populate_mapping(mapping_file)


class Pesci(CellTypeSimilarity):
    def find_output_dirs(self, data_dir):
        output_dirs = []
        for directory in sorted(path for path in data_dir.iterdir() if path.is_dir()):
            info_files = list(directory.glob("*_coexpression_info.tsv"))
            gene_pair_files = list(directory.glob("*_gene_coexpression_table.tsv"))
            if len(info_files) == 1 and len(gene_pair_files) == 1:
                output_dirs.append(directory)
        return output_dirs

    @staticmethod
    def parse_dir_name(directory):
        try:
            species1, species2 = directory.name.split("-", 1)
        except ValueError as exc:
            raise CommandError(f"Invalid PESCI directory name: {directory.name}") from exc
        return species1, species2

    @staticmethod
    def find_file(directory, suffix):
        files = list(directory.glob(f"*{suffix}"))
        if len(files) != 1:
            raise CommandError(f"Expected exactly one {suffix} in {directory}, found {len(files)}")
        return files[0]

    @staticmethod
    def read_coexpression(info_file):
        df = pd.read_csv(info_file, sep="\t")
        cluster_columns = [column for column in df.columns if str(column).endswith("_cell_cluster")]
        if len(cluster_columns) != 2 or "weighted.correlation.score" not in df.columns:
            raise CommandError(f"Unexpected columns in {info_file}: {list(df.columns)}")
        return df, cluster_columns

    @staticmethod
    def read_gene_pairs(gene_pair_file):
        df = pd.read_csv(gene_pair_file, sep="\t")
        gene_columns = [column for column in df.columns if str(column).endswith("_gene")]
        cluster_columns = [column for column in df.columns if str(column).endswith("_cell_cluster")]
        if len(gene_columns) != 2 or len(cluster_columns) != 2:
            raise CommandError(f"Unexpected columns in {gene_pair_file}: {list(df.columns)}")
        return df, cluster_columns, gene_columns

    def build_gene_pair_lookup(self, gene_pair_df, cluster_columns, gene_columns, dataset1, dataset2):
        genes1 = self.preload_genes(dataset1)
        genes2 = self.preload_genes(dataset2)

        cluster1 = gene_pair_df[cluster_columns[0]].map(self.normalize_cell_type)
        cluster2 = gene_pair_df[cluster_columns[1]].map(self.normalize_cell_type)
        gene1 = gene_pair_df[gene_columns[0]].map(genes1)
        gene2 = gene_pair_df[gene_columns[1]].map(genes2)
        valid = gene1.notna() & gene2.notna()

        result = defaultdict(list)
        for c1, c2, g1, g2 in zip(cluster1[valid], cluster2[valid], gene1[valid], gene2[valid]):
            result[(c1, c2)].append([g1, g2])
        return result

    def normalize_cell_type(self, name):
        for prefix in self.datasets.keys():
            prefix = f"{prefix}|"
            if str(name).startswith(prefix):
                name = str(name)[len(prefix):]
                break
        return re.sub(r"[_\s]+", " ", name).strip().lower()

    def populate_output(self, directory):
        species1, species2 = self.parse_dir_name(directory)
        print(f"[PESCI] Processing {species1} -> {species2}: {directory.name}", flush=True)

        dataset1 = self.get_dataset(species1)
        dataset2 = self.get_dataset(species2)

        if self.pair_has_score(dataset1, dataset2, "pesci_score"):
            print(style.WARNING(f"[PESCI] Skipping {species1} -> {species2}: PESCI scores already exist"), flush=True)
            return

        lookup1 = self.build_type_lookup(dataset1, self.normalize_cell_type)
        lookup2 = self.build_type_lookup(dataset2, self.normalize_cell_type)

        info_file = self.find_file(directory, "_coexpression_info.tsv")
        gene_pair_file = self.find_file(directory, "_gene_coexpression_table.tsv")
        info_df, info_cluster_columns = self.read_coexpression(info_file)
        gene_pair_df, gene_pair_cluster_columns, gene_columns = self.read_gene_pairs(gene_pair_file)

        print(f"[PESCI] {len(info_df):,} cell-type pairs, {len(gene_pair_df):,} gene-pair rows", flush=True)

        gene_pair_lookup = self.build_gene_pair_lookup(
            gene_pair_df, gene_pair_cluster_columns, gene_columns, dataset1, dataset2
        )

        cluster1 = info_df[info_cluster_columns[0]].map(self.normalize_cell_type)
        cluster2 = info_df[info_cluster_columns[1]].map(self.normalize_cell_type)
        scores = info_df["weighted.correlation.score"] * 100

        pairs = []
        skipped_elems = []
        skipped = 0

        for c1, c2, score in zip(cluster1, cluster2, scores):
            mt1 = lookup1.get(self.normalize_cell_type(c1))
            mt2 = lookup2.get(self.normalize_cell_type(c2))

            if mt1 is None or mt2 is None:
                if mt1 is None:
                    skipped_elems.append(c1)
                if mt2 is None:
                    skipped_elems.append(c2)
                skipped += 1
                continue

            pairs.append((mt1.id, mt2.id, score, gene_pair_lookup.get((c1, c2), [])))

        self.bulk_upsert(pairs, "pesci_score", "pesci_gene_pairs")
        print(style.SUCCESS(f"[PESCI] Finished {directory.name}: {len(pairs):,} inserted/updated, {skipped:,} skipped"), flush=True)

        if skipped > 0:
            print(style.WARNING(f"Skipped elements: {', '.join(map(str, set(skipped_elems)))}"))

    def run(self, data_dir):
        output_dirs = self.find_output_dirs(data_dir)
        print(f"[PESCI] Found {len(output_dirs):,} output directories", flush=True)
        for directory in output_dirs:
            with transaction.atomic():
                self.populate_output(directory)


class AUCell(CellTypeSimilarity):
    @staticmethod
    def find_rds_files(data_dir):
        return sorted(data_dir.glob("*_*_to_*.rds"))

    @staticmethod
    def parse_rds_name(rds_file):
        match = re.fullmatch(r"(.+?)-(.+?)_(.+?)_to_(.+?)\.rds", rds_file.name)

        if match is None:
            raise CommandError(f"Invalid AUCell RDS filename: {rds_file.name}")

        return match.groups()

    @staticmethod
    def read_rds(rds_file):
        try:
            return read_rds(str(rds_file))
        except Exception as exc:
            raise CommandError(f"Could not read AUCell RDS file {rds_file}: {exc}") from exc

    @staticmethod
    def rds_to_dataframe(data, rds_file):
        x = data["attributes"]["assays"]["attributes"]["data"]["attributes"]["listData"]["data"][0]
        matrix = np.asarray(x["data"]).reshape(tuple(x["attributes"]["dim"]["data"]), order="F")
        d1 = x["attributes"]["dimnames"]["data"][0]["data"]
        d2 = x["attributes"]["dimnames"]["data"][1]["data"]

        auc = (
            pd.DataFrame(matrix, index=d1, columns=d2)
                .rename_axis(index="cell_type_1", columns="cell_type_2")
                .stack()
                .rename("aucell")
                .reset_index()
        )

        # Multiply by 100
        auc["aucell"] *= 100

        return(auc)

    def bulk_upsert(self, objects):
        if not objects:
            return

        table = models.MetacellTypeSimilarity._meta.db_table

        sql = f"""
            INSERT INTO {table} (
                metacelltype_id,
                metacelltype2_id,
                aucell_1to2,
                aucell_2to1
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (metacelltype_id, metacelltype2_id)
            DO UPDATE SET
                aucell_1to2 = COALESCE(
                    EXCLUDED.aucell_1to2,
                    {table}.aucell_1to2
                ),
                aucell_2to1 = COALESCE(
                    EXCLUDED.aucell_2to1,
                    {table}.aucell_2to1
                )
        """

        with connection.cursor() as cursor:
            cursor.executemany(sql, objects)

    def is_reversed(self, dataset1, dataset2, species1):
        """Return True if dataset1/dataset2 exists in the database in reverse order."""
        reversed = models.MetacellTypeSimilarity.objects.filter(
            metacelltype__dataset__internal_id=dataset2,
            metacelltype2__dataset__internal_id=dataset1,
        ).exists()

        if not dataset1.startswith(species1):
            reversed = not reversed

        return reversed

    def populate_rds(self, rds_file):
        dataset1, dataset2, species1, species2 = self.parse_rds_name(rds_file)

        print(f"[AUCELL] Processing {dataset1} -> {dataset2}: {rds_file.name}", flush=True)
        source_dataset = self.get_dataset(dataset1)
        target_dataset = self.get_dataset(dataset2)
        reverse = self.is_reversed(dataset1, dataset2, species1)

        source_lookup = self.build_type_lookup(source_dataset, self.normalize_cell_type)
        target_lookup = self.build_type_lookup(target_dataset, self.normalize_cell_type)
        df = self.rds_to_dataframe(self.read_rds(rds_file), rds_file)

        required_columns = {"cell_type_1", "cell_type_2", "aucell"}
        if not required_columns.issubset(df.columns):
            raise CommandError(f"Unexpected AUCell data format in {rds_file}: {list(df.columns)}")

        pairs = []
        skipped_elems = []
        skipped = 0

        for c1, c2, score in df[["cell_type_1", "cell_type_2", "aucell"]].itertuples(index=False, name=None):
            if reverse:
                c1, c2 = c2, c1

            mt1 = source_lookup.get(self.normalize_cell_type(c1))
            mt2 = target_lookup.get(self.normalize_cell_type(c2))

            if mt1 is None or mt2 is None:
                if mt1 is None:
                    skipped_elems.append(c1)
                if mt2 is None:
                    skipped_elems.append(c2)

                skipped += 1
                continue

            score_1to2, score_2to1 = (None, score) if reverse else (score, None)
            pairs.append((mt1.id, mt2.id, score_1to2, score_2to1))

        self.bulk_upsert(pairs)

        msg = f"[AUCELL] Finished {rds_file.name}: {len(pairs):,} inserted/updated, {skipped:,} skipped"
        print(style.SUCCESS(msg), flush=True)
        if skipped > 0:
            print(style.WARNING(f"Skipped elements: {', '.join(map(str, set(skipped_elems)))}"))

    def run(self, data_dir):
        rds_files = self.find_rds_files(data_dir)
        print(f"[AUCELL] Found {len(rds_files):,} RDS files", flush=True)
        for rds_file in rds_files:
            with transaction.atomic():
                self.populate_rds(rds_file)


class Command(BaseCommand):
    help = "Populate metacell-type similarity scores from SAMAP and/or PESCI results."

    def add_arguments(self, parser):
        parser.add_argument("--samap", type=Path)
        parser.add_argument("--pesci", type=Path)
        parser.add_argument("--aucell", type=Path)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        samap_dir = options["samap"]
        pesci_dir = options["pesci"]
        aucell_dir = options["aucell"]

        if samap_dir is None and pesci_dir is None and aucell_dir is None:
            raise CommandError("Specify at least one of --samap, --pesci or --aucell.")

        for name, data_dir in (("SAMap", samap_dir), ("Pesci", pesci_dir), ("AUCell", aucell_dir)):
            if data_dir is not None and not data_dir.is_dir():
                raise CommandError(f"{name} data directory does not exist: {data_dir}")

        if options["dry_run"]:
            with transaction.atomic():
                self.run(samap_dir, pesci_dir, aucell_dir)
                transaction.set_rollback(True)
        else:
            self.run(samap_dir, pesci_dir, aucell_dir)

    def run(self, samap_dir, pesci_dir, aucell_dir):
        if samap_dir is not None:
            SAMap().run(samap_dir)

        if pesci_dir is not None:
            Pesci().run(pesci_dir)

        if aucell_dir is not None:
            AUCell().run(aucell_dir)
