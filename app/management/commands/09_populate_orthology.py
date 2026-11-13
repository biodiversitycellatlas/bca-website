#!/usr/bin/env python3

from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

from app import models


class Command(BaseCommand):
    help = "Check orthology pair files against genes in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "data_dir",
            help="Directory containing *.orthology_pairs.tsv.gz files.",
        )

    def find_orthology_files(self, data_dir):
        return sorted(
            Path(data_dir).glob("*.orthology_pairs.tsv.gz")
        )

    def parse_filename(self, path):
        suffix = ".orthology_pairs.tsv.gz"

        if not path.name.endswith(suffix):
            return None, None

        name = path.name[: -len(suffix)]

        if "-" not in name:
            return None, None

        species1, species2 = name.split("-", 1)

        return species1, species2

    def get_dataset(self, internal_id):
        return (
            models.Dataset.objects
            .select_related("species")
            .filter(internal_id=internal_id)
            .first()
        )

    def read_pairs(self, path):
        df = pd.read_csv(
            path,
            sep="\t",
            header=None,
            names=["gene1", "gene2"],
            dtype=str,
            compression="gzip",
        )

        df["gene1"] = df["gene1"].fillna("").str.strip()
        df["gene2"] = df["gene2"].fillna("").str.strip()

        return df[
            (df["gene1"] != "")
            & (df["gene2"] != "")
        ]

    def build_gene_lookup(self, dataset):
        genes = models.Gene.objects.filter(
            species=dataset.species,
        )

        return {
            gene.name: gene
            for gene in genes
        }

    def check_file(self, path):
        species1, species2 = self.parse_filename(path)

        if not species1 or not species2:
            self.stdout.write(
                self.style.WARNING(
                    f"[SKIP] Invalid filename: {path.name}"
                )
            )
            return {
                "pairs": 0,
                "missing1": [],
                "missing2": [],
            }

        dataset1 = self.get_dataset(species1)
        dataset2 = self.get_dataset(species2)

        if dataset1 is None:
            self.stdout.write(
                self.style.ERROR(
                    f"[SKIP] Dataset not found: {species1}"
                )
            )
            return {
                "pairs": 0,
                "missing1": [],
                "missing2": [],
            }

        if dataset2 is None:
            self.stdout.write(
                self.style.ERROR(
                    f"[SKIP] Dataset not found: {species2}"
                )
            )
            return {
                "pairs": 0,
                "missing1": [],
                "missing2": [],
            }

        df = self.read_pairs(path)

        gene_lookup1 = self.build_gene_lookup(dataset1)
        gene_lookup2 = self.build_gene_lookup(dataset2)

        missing1 = set()
        missing2 = set()

        for row in df.itertuples(index=False):
            if row.gene1 not in gene_lookup1:
                missing1.add(row.gene1)

            if row.gene2 not in gene_lookup2:
                missing2.add(row.gene2)

        self.stdout.write("")
        self.stdout.write(f"[CHECK] {path.name}")
        self.stdout.write(
            f"  {species1}: {dataset1.species.scientific_name}"
        )
        self.stdout.write(
            f"  {species2}: {dataset2.species.scientific_name}"
        )
        self.stdout.write(
            f"  Orthology pairs: {len(df):,}"
        )
        self.stdout.write(
            f"  Missing {species1}: {len(missing1):,}"
        )
        self.stdout.write(
            f"  Missing {species2}: {len(missing2):,}"
        )

        if missing1:
            self.stdout.write(
                f"    Examples: {', '.join(sorted(missing1)[:6])}"
            )

        if missing2:
            self.stdout.write(
                f"    Examples: {', '.join(sorted(missing2)[:6])}"
            )

        return {
            "pairs": len(df),
            "missing1": missing1,
            "missing2": missing2,
        }

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])

        if not data_dir.exists():
            raise FileNotFoundError(
                f"Directory does not exist: {data_dir}"
            )

        paths = self.find_orthology_files(data_dir)

        self.stdout.write(
            f"Found {len(paths):,} orthology pair files."
        )

        total_pairs = 0
        total_missing = 0

        for path in paths:
            result = self.check_file(path)

            total_pairs += result["pairs"]
            total_missing += (
                len(result["missing1"])
                + len(result["missing2"])
            )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(
            f"Files checked : {len(paths):,}"
        )
        self.stdout.write(
            f"Pairs checked : {total_pairs:,}"
        )
        self.stdout.write(
            f"Missing genes : {total_missing:,}"
        )
