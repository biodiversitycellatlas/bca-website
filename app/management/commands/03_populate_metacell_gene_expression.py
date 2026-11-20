#!/usr/bin/env python3

import gzip
import re
from pathlib import Path

import csv
import io

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import connection
from scipy.io import mmread

from app import models


# ============================================================
# File helpers
# ============================================================

def open_text(path):
    path = str(path)

    if path.endswith(".gz"):
        return gzip.open(path, "rt")

    return open(path, "r")


def read_lines(path):
    with open_text(path) as f:
        return [x.strip() for x in f if x.strip()]


def read_metacell_ids(path):
    return read_lines(path)


def read_gene_ids(path):
    return read_lines(path)


# ============================================================
# Dataset discovery
# ============================================================

def find_datasets(data_dir):
    data_dir = Path(data_dir).expanduser()

    pattern = re.compile(r"^(.+)\.metacell\.umi\.counts\.mtx\.gz$")
    datasets = set()
    for path in data_dir.glob("*.metacell.umi.counts.mtx.gz"):
        match = pattern.match(path.name)

        if match:
            datasets.add(match.group(1))

    return sorted(datasets)


# ============================================================
# Dataset files
# ============================================================

def get_files(data_dir, internal_id):
    data_dir = Path(data_dir).expanduser()

    return {
        "umi": data_dir / f"{internal_id}.metacell.umi.counts.mtx.gz",
        "genes": data_dir / f"{internal_id}.metacell.umi.geneID.txt",
        "metacells": data_dir / f"{internal_id}.metacell.umi.metacellID.txt",
        "fold_change": data_dir / f"{internal_id}.mc_fp.tsv.gz",
    }


def check_files(files):
    required = ("umi", "genes", "metacells", "fold_change")

    return [files[key].name for key in required if not files[key].exists()]


def get_dataset(internal_id):
    return (models.Dataset.objects.filter(internal_id=internal_id).select_related("species").first())


def get_metacells(dataset, metacell_names):
    qs = models.Metacell.objects.filter(dataset=dataset).only("id", "name")
    mc_map = { str(mc.name): mc.id for mc in qs }

    missing = [ name for name in metacell_names if str(name) not in mc_map ]

    if missing:
        print(f"[ERROR] {dataset.internal_id}: {len(missing):,} metacells from the input are missing in the database")
        if len(missing) <= 20:
            print("  Missing metacells:")
            for name in missing:
                print(f"    {name}")

        return None

    return [mc_map[str(name)] for name in metacell_names]


def create_missing_genes(species, gene_names):
    existing = {
        name: gene_id
        for name, gene_id in (
            models.Gene.objects.filter(species=species, name__in=gene_names).values_list("name", "id")
        )
    }

    missing = [name for name in gene_names if name not in existing]

    if missing:
        print(f"  Creating {len(missing):,} missing genes...")
        models.Gene.objects.bulk_create(
            [models.Gene(species=species, name=name) for name in missing],
            ignore_conflicts=True,
            batch_size=10000,
        )
        existing = {
            name: gene_id
            for name, gene_id in (
                models.Gene.objects.filter(species=species, name__in=gene_names).values_list("name", "id")
            )
        }

    return existing


def read_fold_change(path):
    df = pd.read_csv(path, sep="\t", compression="gzip", index_col=0)

    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)

    return df


def normalize_gene_name(name, species):
    name = str(name)

    if str(species) == "Schistosoma mansoni":
        return name.replace("Smp_", "Smp-")

    return name


def get_table_name():
    return models.MetacellGeneExpression._meta.db_table


def copy_rows(cursor, table, rows):
    if not rows:
        return 0

    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerows(rows)
    output.seek(0)

    sql = f"""
        COPY {table} ( dataset_id, gene_id, metacell_id, fold_change, umi_raw, umifrac )
        FROM STDIN WITH ( FORMAT csv, DELIMITER E'\\t', NULL '\\N' )
    """

    with cursor.copy(sql) as copy:
        copy.write(output.getvalue())

    return len(rows)


def delete_existing(dataset_id):
    table = get_table_name()

    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE dataset_id = %s", [dataset_id])


def populate_dataset(data_dir, internal_id, replace=False, batch_size=100000):
    files = get_files(data_dir, internal_id)

    missing = check_files(files)
    if missing:
        print(f"[SKIP] {internal_id}: missing {', '.join(missing)}")
        return

    dataset = get_dataset(internal_id)
    if dataset is None:
        print(f"[SKIP] {internal_id}: dataset does not exist in database")
        return

    existing = (models.MetacellGeneExpression.objects.filter(dataset=dataset).exists())

    if not replace and existing:
        print(f"[SKIP] {internal_id}: metacell gene expression data already exists")
        return

    # --------------------------------------------------------
    # Read IDs
    # --------------------------------------------------------

    metacell_names = read_metacell_ids(
        files["metacells"]
    )

    gene_names = read_gene_ids(
        files["genes"]
    )

    print()
    print("=" * 70)
    print(f"[LOAD] {internal_id}")
    print(f"  Species: {dataset.species}")
    print(
        f"  Metacells: {len(metacell_names):,}"
    )
    print(
        f"  Genes: {len(gene_names):,}"
    )

    # --------------------------------------------------------
    # Metacells
    # --------------------------------------------------------

    metacell_ids = get_metacells(
        dataset,
        metacell_names,
    )

    if metacell_ids is None:
        return

    gene_map = create_missing_genes(dataset.species, gene_names)

    missing_genes = [name for name in gene_names if name not in gene_map]

    if missing_genes:
        raise ValueError(f"{len(missing_genes):,} genes could not be found or created in the database")

    gene_ids = [gene_map[name] for name in gene_names]

    if replace:
        print("  Removing existing metacell gene expression...")
        delete_existing(dataset.id)

    print("  Reading fold-change matrix...")
    fold_change = read_fold_change(files["fold_change"])

    print(f"  Fold-change matrix: {fold_change.shape[0]:,} genes x {fold_change.shape[1]:,} metacells")
    print("  Reading UMI matrix...")
    umi = mmread(files["umi"]).tocsc()

    expected_shape = (len(gene_names), len(metacell_names))

    if umi.shape != expected_shape:
        raise ValueError(f"UMI matrix shape {umi.shape} does not match expected {expected_shape} (genes x metacells)")
    print(f"  UMI matrix: {umi.shape[0]:,} genes x {umi.shape[1]:,} metacells")

    metacell_totals = np.asarray(umi.sum(axis=0)).ravel()

    table = get_table_name()
    dataset_id = dataset.id

    total_metacells = umi.shape[1]

    inserted = 0
    skipped_empty = 0

    with connection.cursor() as django_cursor:
        cursor = django_cursor.cursor
        rows = []

        for mc_col in range(total_metacells):
            start = umi.indptr[mc_col]
            end = umi.indptr[mc_col + 1]

            total_umi = metacell_totals[mc_col]

            if total_umi == 0:
                skipped_empty += 1
                continue

            mc_id = metacell_ids[mc_col]
            mc_name = str(metacell_names[mc_col])

            for pos in range(start, end):
                gene_idx = int(umi.indices[pos])
                umi_raw = umi.data[pos]
                # Explicitly ignore zero values
                if umi_raw == 0:
                    continue

                gene_name = gene_names[gene_idx]
                gene_id = gene_ids[gene_idx]

                umifrac = float(umi_raw) * 10000.0 / float(total_umi)
                fold_gene = normalize_gene_name(gene_name, dataset.species)
                fold_change_value = None
                if fold_gene in fold_change.index and mc_name in fold_change.columns:
                    value = fold_change.at[fold_gene, mc_name]

                    if pd.notna(value):
                        fold_change_value = float(value)
                fold_change_value <- r"\N" if fold_change_value is None else fold_change_value
                rows.append((dataset_id, gene_id, mc_id, fold_change_value, float(umi_raw), umifrac))

                if len(rows) >= batch_size:
                    inserted += copy_rows(cursor, table, rows)
                    rows.clear()

            if mc_col % 100 == 0:
                print(f"  Processed {mc_col:,}/{total_metacells:,} metacells; {inserted:,} rows inserted")

        if rows:
            inserted += copy_rows(cursor, table, rows)
            rows.clear()

    connection.commit()
    print(f"  Non-zero expression rows: {inserted:,}")
    print(f"  Empty metacells skipped: {skipped_empty:,}")
    print(f"[DONE] {internal_id}")


def populate(data_dir, dataset_id=None, species=None, replace=False):
    data_dir = Path(data_dir).expanduser()

    if dataset_id:
        datasets = [dataset_id]
        print(f"Mode: SINGLE DATASET")
        print(f"Dataset: {dataset_id}")
    elif species:
        print(f"Mode: SPECIES")
        print(f"Species: {species}")
        all_datasets = find_datasets(data_dir)

        datasets = []
        for internal_id in all_datasets:
            dataset = get_dataset(internal_id)
            if dataset is None:
                print(f"[SKIP] {internal_id}: dataset does not exist in database")
                continue

            if str(dataset.species) == species:
                datasets.append(internal_id)

        print(f"Found {len(datasets):,} matching dataset(s).")
    else:
        print("Mode: ALL datasets")
        datasets = find_datasets(data_dir)
        print(f"Found {len(datasets):,} dataset(s).")

    if not datasets:
        print("[WARNING] No datasets to load.")

        return

    for internal_id in datasets:
        dataset = get_dataset(internal_id)
        if dataset is None:
            print(f"[SKIP] {internal_id}: dataset does not exist in database")
            continue

        print(f"[FOUND] {internal_id} (species: {dataset.species})")

        try:
            populate_dataset(data_dir, internal_id, replace=replace)
        except Exception as exc:
            connection.rollback()
            print(f"[ERROR] {internal_id}: {exc}")
            raise


class Command(BaseCommand):

    help = "Populate metacell gene expression from metacell UMI files."

    def add_arguments(self, parser):
        parser.add_argument("data_dir", help="Directory containing the metacell expression files.")
        parser.add_argument(
            "--dataset",
            dest="dataset_id",
            default=None,
            help="Optional dataset internal_id. Example: --dataset triadh01",
        )
        parser.add_argument("--species", default=None, help="Optional species name. If omitted, load all datasets.")
        parser.add_argument("--replace", action="store_true", help="Delete existing expression data before loading.")

    def handle(self, *args, **options):
        populate(options["data_dir"], options["dataset_id"], options["species"], options["replace"])
