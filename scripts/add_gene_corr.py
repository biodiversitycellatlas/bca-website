#!/usr/bin/env python3

from django.core.exceptions import ValidationError
from django.db import connection

import os

from rds2py import read_rds
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from scipy.stats import t

import math
import time
import functools
import psycopg2

from app import models
from scripts.add_data_to_db import batch_raw_insert

# Auto-flush print statements
print = functools.partial(print, flush=True)

####### Main functions

def safe_round(val, digits=2):
    return round(val, digits) if not math.isnan(val) else None

def calculate_corr(df):
    spearman = df.corr(method='spearman')
    pearson  = df.corr(method='pearson')
    
    spearman_mask = np.triu(np.ones(spearman.shape), k=1).astype(bool)
    pearson_mask  = np.triu(np.ones(pearson.shape), k=1).astype(bool)
    
    spearman_upper = spearman.where(spearman_mask).stack().reset_index(allow_duplicates=True)
    pearson_upper  = pearson.where(pearson_mask).stack().reset_index(allow_duplicates=True)
    
    spearman_upper.columns = ['gene_id', 'gene2_id', 'spearman']
    pearson_upper.columns  = ['gene_id', 'gene2_id', 'pearson']
    
    merged = spearman_upper.merge(pearson_upper, on=['gene_id', 'gene2_id'])
    print(merged.shape)

    merged = merged.drop_duplicates(subset=merged.columns[:2])
    merged[['spearman', 'pearson']] = (merged[['spearman', 'pearson']] * 100).round().astype(int)

    # Drop correlation coefficients of 0
    merged = merged[~(merged == 0).all(axis=1)]
    merged['dataset_id'] = d.id
    return merged


def save_dataset_gene_corr(d):    
    print(d)
    start_time = time.time()

    print("Getting expression values per metacell...")
    mge = d.mge.filter(fold_change__gte=2).values(
        'gene__id', 'metacell__id', 'fold_change')

    print("Converting to data frame...")
    df = pd.DataFrame(mge)
    df_pivot = df.pivot(index='metacell__id', columns='gene__id', values='fold_change')
    n_metacells, n_genes = df_pivot.shape
    print(df_pivot.shape)

    print("Calculating correlations...")
    df_long = calculate_corr(df_pivot)
    print(df_long)
    
    elapsed_time = round(time.time() - start_time,2)
    print(f"Elapsed time: {elapsed_time} seconds")
    start_time = time.time()

    print('Saving to database...')
    connection = psycopg2.connect(host=os.environ.get("POSTGRES_HOST"))
    with connection.cursor() as cursor:
        batch_raw_insert(cursor, models.GeneCorrelation, df_long.keys(), df_long)
    connection.close()

    elapsed_time = round(time.time() - start_time,2)
    print(f"Elapsed time: {elapsed_time} seconds")

datasets = Dataset.objects.all()
datasets = Dataset.objects.filter(species__scientific_name='Trichoplax adhaerens')
for d in datasets:
    save_dataset_gene_corr(d)
