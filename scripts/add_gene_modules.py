#!/usr/bin/env python3

import csv
import fnmatch
import functools
from pathlib import Path

from scripts.utils import load_config

from app.models import Dataset, GeneModule

# Auto-flush print statements
print = functools.partial(print, flush=True)

# Main functions

config = load_config("data/raw/config.yaml")
dir = "data/raw"


def parse_dataset(s):
    if "(" in s:
        species = s.split("(")[0].strip()
        dataset = s.split("(")[1].rstrip(")").strip()
    else:
        species = s.strip()
        dataset = None
    return species, dataset


def update_gene_modules(file_path, species, dataset):
    try:
        dataset = Dataset.objects.get(species__scientific_name=species, name=dataset)
    except Dataset.DoesNotExist:
        print(f"Dataset not found: {species} / {dataset}")
        return

    with open(file_path) as file_path:
        reader = csv.DictReader(file_path, delimiter="\t")
        for row in reader:
            gene_name = row["gene"]
            module_name = row["gene_module"]
            membership_score = float(row["membership_score"])

            try:
                gene = dataset.species.genes.get(name=gene_name)
            except dataset.species.genes.model.DoesNotExist:
                continue

            GeneModule.objects.update_or_create(
                dataset=dataset,
                gene=gene,
                name=module_name,
                membership_score=membership_score,
            )


datasets = Dataset.objects.all()
for key in config:
    i = config[key]
    if "data_subdir" in i.keys():
        subdir = i["data_subdir"]
        dataset = i["species"]

        base_path = Path(f"{dir}/{subdir}")
        for file in base_path.iterdir():
            if fnmatch.fnmatch(file.name.lower(), f"wgcna*{key.lower()}*.csv"):
                print(f"===== {dataset} =====")
                species, dataset = parse_dataset(dataset)
                update_gene_modules(file, species, dataset)
