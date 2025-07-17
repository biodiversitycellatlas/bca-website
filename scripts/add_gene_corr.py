#!/usr/bin/env python3


import functools
import math
import os
import time

import numpy as np
import pandas as pd
import psycopg2

from app import models
from scripts.add_data_to_db import batch_raw_insert

# Auto-flush print statements
print = functools.partial(print, flush=True)

####### Main functions


def safe_round(val, digits=2):
    return round(val, digits) if not math.isnan(val) else None


def get_top_bottom(df, score_col, n=100):
    return pd.concat(
        [
            df.sort_values(score_col, ascending=False).groupby("gene_id").head(n),
            df.sort_values(score_col, ascending=True).groupby("gene_id").head(n),
        ]
    )


def filter_top_bottom_only(merged):
    # Remove self-correlations and duplicate gene pairs (treat A–B same as B–A)
    merged = merged.loc[merged["gene_id"] != merged["gene2_id"]].copy()
    merged["pair"] = list(
        zip(
            np.minimum(merged["gene_id"], merged["gene2_id"]),
            np.maximum(merged["gene_id"], merged["gene2_id"]),
        )
    )
    merged = merged.drop_duplicates(subset="pair").drop(columns="pair")

    # Ge top/bottom hits
    top_bottom_spearman = get_top_bottom(merged, "spearman", n=100)
    top_bottom_pearson = get_top_bottom(merged, "pearson", n=100)

    # Combine and drop duplicates (if same pair appears in both)
    filtered = pd.concat([top_bottom_spearman, top_bottom_pearson]).drop_duplicates()
    print("-> Top/bottom filtering: ", filtered.shape)
    return filtered


def calculate_corr(df):
    spearman = df.corr(method="spearman")
    pearson = df.corr(method="pearson")

    # spearman_mask = np.triu(np.ones(spearman.shape), k=1).astype(bool)
    # pearson_mask  = np.triu(np.ones(pearson.shape), k=1).astype(bool)

    # spearman_upper = spearman.where(spearman_mask).stack().reset_index(allow_duplicates=True)
    # pearson_upper  = pearson.where(pearson_mask).stack().reset_index(allow_duplicates=True)
    spearman_upper = spearman.stack().reset_index(allow_duplicates=True)
    pearson_upper = pearson.stack().reset_index(allow_duplicates=True)

    spearman_upper.columns = ["gene_id", "gene2_id", "spearman"]
    pearson_upper.columns = ["gene_id", "gene2_id", "pearson"]

    merged = spearman_upper.merge(pearson_upper, on=["gene_id", "gene2_id"])
    print(merged.shape)

    # Drop duplicates
    merged = merged.drop_duplicates(subset=merged.columns[:2])
    merged[["spearman", "pearson"]] = merged[["spearman", "pearson"]].round(2)

    # Drop correlation coefficients of 0
    merged = merged[~(merged == 0).all(axis=1)]
    merged["dataset_id"] = d.id

    print("Filtering top/bottom hits...")
    filtered = filter_top_bottom_only(merged)
    print(filtered.shape)
    return filtered


def save_dataset_gene_corr(d):
    start_time = time.time()

    print("Getting metacell gene expression values for genes with FC >= 2...")
    genes = (
        d.mge.filter(fold_change__gte=2).values_list("gene__id", flat=True).distinct()
    )
    mge = d.mge.filter(gene__id__in=genes).values(
        "gene__id", "metacell__id", "fold_change"
    )

    print("Converting to data frame...")
    df = pd.DataFrame(mge)
    df_pivot = df.pivot(index="metacell__id", columns="gene__id", values="fold_change")
    n_metacells, n_genes = df_pivot.shape
    print(df_pivot.shape)

    print("Calculating correlations...")
    df_long = calculate_corr(df_pivot)

    elapsed_time = round(time.time() - start_time, 2)
    print(f"Elapsed time: {elapsed_time} seconds")
    start_time = time.time()

    print("Saving to database...")
    connection = psycopg2.connect(host=os.environ.get("POSTGRES_HOST"))
    with connection.cursor() as cursor:
        batch_raw_insert(cursor, models.GeneCorrelation, df_long.keys(), df_long)
    connection.close()

    elapsed_time = round(time.time() - start_time, 2)
    print(f"Elapsed time: {elapsed_time} seconds")


datasets = Dataset.objects.all()
# datasets = Dataset.objects.filter(species__scientific_name='Trichoplax adhaerens')
for d in datasets:
    if not d.gene_corr.exists():
        print(f"\n====== {d.slug} ======")
        save_dataset_gene_corr(d)
