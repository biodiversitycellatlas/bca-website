from django.core.exceptions import ValidationError
from django.db.models import F, Count, Avg, Sum, OuterRef, Subquery

from collections import Counter
from rds2py import read_rds
import subprocess
import time

import csv
import json
import yaml

import numpy as np
import pandas as pd

import urllib.request
import urllib.parse
import warnings
import re

from app import models

import functools
import psycopg2
import psutil
import io

# Auto-flush print statements
print = functools.partial(print, flush=True)

####### Utility functions


def print_progress(index, total):
    perc = int(index / total * 100)
    msg = f"{perc}% ({index} out of {total})"
    print(msg)
    return msg


def load_config(filename="config.yaml"):
    with open(filename, "r") as f:
        data = yaml.safe_load(f)
    return data


def parse_dataset(s):
    if "(" in s:
        species = s.split("(")[0].strip()
        dataset = s.split("(")[1].rstrip(")").strip()
    else:
        species = s.strip()
        dataset = None
    return species, dataset


def print_memory_usage(val=" "):
    mem = psutil.virtual_memory()
    mem_used = mem.used / 1024**2
    mem_total = mem.total / 1024**2
    mem_free = mem.available / 1024**2
    print(
        f"Memory {val} | Used {mem_used:.2f} MB out of {mem_total:.2f} MB (free: {mem_free:.2f} MB)"
    )


def validate_and_bulk_create(obj, arr):
    # for data in arr:
    #    try:
    #        data.full_clean()
    #    except ValidationError:
    #        print(f"Validation error for {instance}: {e}")

    return obj.objects.bulk_create(arr, ignore_conflicts=True)


def batch_raw_insert(cursor, model, cols, batch):
    output = io.StringIO()
    if isinstance(batch, pd.DataFrame):
        batch.to_csv(output, sep="\t", index=False, header=False)
    else:
        writer = csv.writer(output, delimiter="\t")
        writer.writerows(batch)
    output.seek(0)

    table = model._meta.db_table
    columns = ", ".join(cols)
    sql = f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')"
    cursor.copy_expert(sql, output)
    cursor.connection.commit()
    return cursor


def perform_subquery(obj, expr):
    """Return subquery for aggregated statistics per object."""
    subquery = Subquery(
        obj.filter(id=OuterRef("id")).annotate(expr=expr).values("expr")[:1]
    )
    return subquery
