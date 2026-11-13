#!/usr/bin/env python3

import gzip
import re
from pathlib import Path

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from scipy.io import mmread

from app import models


class Command(BaseCommand):
    help = "Populate CytoTRACE and median UMI values for single cells and metacells."

    def open_text(self, path):
        path = str(path)
        return gzip.open(path, "rt") if path.endswith(".gz") else open(path, "r")

    def read_lines(self, path):
        with self.open_text(path) as f:
            return [x.strip() for x in f if x.strip()]

    def find_datasets(self, data_dir):
        data_dir = Path(data_dir)
        pattern = re.compile(r"^(.+)\.cytotrace\.tsv\.gz$")
        return sorted(
            match.group(1)
            for path in data_dir.glob("*.cytotrace.tsv.gz")
            if (match := pattern.match(path.name))
        )

    def get_files(self, cytotrace_dir, counts_dir, internal_id):
        cytotrace_dir = Path(cytotrace_dir)
        counts_dir = Path(counts_dir)
        return {
            "cytotrace": cytotrace_dir / f"{internal_id}.cytotrace.tsv.gz",
            "counts": counts_dir / f"{internal_id}.counts.mtx",
            "genes": counts_dir / f"{internal_id}.geneID.txt",
            "cells": counts_dir / f"{internal_id}.cellID.txt",
        }

    def check_files(self, files):
        return [files[key].name for key in ("cytotrace", "counts", "genes", "cells") if not files[key].exists()]

    def get_dataset(self, internal_id):
        return models.Dataset.objects.filter(internal_id=internal_id).first()

    def get_single_cells(self, dataset):
        return {
            str(name): {"id": cell_id, "metacell_id": metacell_id}
            for cell_id, name, metacell_id in models.SingleCell.objects.filter(dataset=dataset)
            .values_list("id", "name", "metacell_id")
        }

    def read_cytotrace(self, path):
        df = pd.read_csv(path, sep=r"\s+", engine="python")
        if "cell" not in df.columns or "CytoTRACE" not in df.columns:
            raise ValueError(f"{path.name} must contain 'cell' and 'CytoTRACE' columns")
        df["cell"] = df["cell"].astype(str)
        df["CytoTRACE"] = pd.to_numeric(df["CytoTRACE"], errors="coerce")
        return df.dropna(subset=["CytoTRACE"])

    def median_sparse_column(self, data, n_rows):
        if len(data) == 0:
            return 0.0
        return float(np.median(data))

    def calculate_cell_median_umis(self, matrix):
        matrix = matrix.tocsc()
        matrix.sort_indices()
        n_genes, n_cells = matrix.shape
        medians = np.zeros(n_cells, dtype=float)

        for cell_idx in range(n_cells):
            start, end = matrix.indptr[cell_idx], matrix.indptr[cell_idx + 1]
            medians[cell_idx] = self.median_sparse_column(matrix.data[start:end], n_genes)

        return medians

    def update_single_cells(self, dataset, cell_names, cell_records, cytotrace, median_umis):
        objects = []

        for cell_idx, cell_name in enumerate(cell_names):
            record = cell_records.get(str(cell_name))
            if record is None:
                continue

            cell = models.SingleCell(id=record["id"], dataset=dataset)
            changed = False

            if median_umis is not None:
                cell.median_umis = float(median_umis[cell_idx])
                changed = True

            if cytotrace is not None:
                value = cytotrace.get(str(cell_name))
                if value is not None:
                    cell.cytotrace = float(value)
                    changed = True

            if changed:
                objects.append(cell)

        if objects:
            models.SingleCell.objects.bulk_update(objects, ["median_umis", "cytotrace"], batch_size=10000)

        return objects

    def calculate_metacell_medians(self, cell_names, cell_records, cytotrace, median_umis):
        metacell_values = {}

        for cell_idx, cell_name in enumerate(cell_names):
            record = cell_records.get(str(cell_name))
            if record is None or record["metacell_id"] is None:
                continue

            metacell_id = record["metacell_id"]
            values = metacell_values.setdefault(metacell_id, {"cytotrace": [], "median_umis": []})

            if median_umis is not None:
                values["median_umis"].append(float(median_umis[cell_idx]))

            if cytotrace is not None:
                value = cytotrace.get(str(cell_name))
                if value is not None:
                    values["cytotrace"].append(float(value))

        return metacell_values

    def update_metacells(self, dataset, metacell_values):
        if not metacell_values:
            return

        objects = list(models.Metacell.objects.filter(dataset=dataset, id__in=metacell_values))

        for metacell in objects:
            values = metacell_values.get(metacell.id)
            if values is None:
                continue

            if values["cytotrace"]:
                metacell.cytotrace = float(np.median(values["cytotrace"]))

            if values["median_umis"]:
                metacell.median_umis = float(np.median(values["median_umis"]))

        if objects:
            models.Metacell.objects.bulk_update(objects, ["cytotrace", "median_umis"], batch_size=10000)

    def populate_dataset(self, cytotrace_dir, counts_dir, internal_id):
        files = self.get_files(cytotrace_dir, counts_dir, internal_id)
        missing = self.check_files(files)

        if missing:
            print(f"[SKIP] {internal_id}: missing {', '.join(missing)}")
            return

        dataset = self.get_dataset(internal_id)
        if dataset is None:
            print(f"[SKIP] {internal_id}: dataset does not exist in database")
            return

        print(f"[LOAD] {internal_id}")

        cell_names = self.read_lines(files["cells"])
        gene_names = self.read_lines(files["genes"])
        cell_records = self.get_single_cells(dataset)

        print(f"  Cells in matrix: {len(cell_names):,}")
        print(f"  Genes in matrix: {len(gene_names):,}")
        print(f"  Single cells in database: {len(cell_records):,}")

        if not cell_records:
            print(f"[SKIP] {internal_id}: no single cells found in database")
            return

        print("  Reading CytoTRACE...")
        cytotrace_df = self.read_cytotrace(files["cytotrace"])
        cytotrace = dict(zip(cytotrace_df["cell"], cytotrace_df["CytoTRACE"]))
        print(f"  CytoTRACE values: {len(cytotrace):,}")

        print("  Reading counts matrix...")
        counts = mmread(files["counts"])

        expected_shape = (len(gene_names), len(cell_names))
        if counts.shape != expected_shape:
            raise ValueError(
                f"Counts matrix shape {counts.shape} does not match "
                f"{len(gene_names)} genes x {len(cell_names)} cells"
            )

        print(f"  Counts matrix: {counts.shape[0]:,} genes x {counts.shape[1]:,} cells")
        print(f"  Non-zero entries: {counts.nnz:,}")

        counts = counts.tocsc()
        counts.sort_indices()

        print("  First 10 cells - non-zero UMI values:")

        for cell_idx in range(min(10, counts.shape[1])):
            start = counts.indptr[cell_idx]
            end = counts.indptr[cell_idx + 1]
            values = counts.data[start:end]

            print(
                f"    Cell {cell_idx + 1} ({cell_names[cell_idx]}): "
                f"{len(values):,} non-zero genes, "
                f"UMIs = {values.tolist()}"
            )

        print("  Calculating median UMI per cell...")
        median_umis = self.calculate_cell_median_umis(counts)

        print("  Updating single-cell values...")
        updated_cells = self.update_single_cells(dataset, cell_names, cell_records, cytotrace, median_umis)
        print(f"  Updated single cells: {len(updated_cells):,}")

        print("  Calculating metacell medians...")
        metacell_values = self.calculate_metacell_medians(cell_names, cell_records, cytotrace, median_umis)
        print(f"  Metacells with values: {len(metacell_values):,}")

        print("  Updating metacells...")
        self.update_metacells(dataset, metacell_values)

        print(f"[DONE] {internal_id}")

    def populate(self, cytotrace_dir, counts_dir):
        datasets = self.find_datasets(cytotrace_dir)
        print(f"Found {len(datasets)} datasets.")

        for internal_id in datasets:
            try:
                self.populate_dataset(cytotrace_dir, counts_dir, internal_id)
            except Exception as exc:
                print(f"[ERROR] {internal_id}: {exc}")
                raise

    def add_arguments(self, parser):
        parser.add_argument("cytotrace_dir", help="Directory containing CytoTRACE files.")
        parser.add_argument("counts_dir", help="Directory containing single-cell expression files.")

    def handle(self, *args, **options):
        self.populate(options["cytotrace_dir"], options["counts_dir"])
