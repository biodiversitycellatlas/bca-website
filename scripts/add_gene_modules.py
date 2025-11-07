#!/usr/bin/env python3

import csv
import fnmatch
import functools
import rds2py
import numpy as np
from pathlib import Path

from scripts.utils import load_config

from app.models import (
    Dataset,
    Metacell,
    GeneModule,
    GeneModuleMembership,
    GeneModuleEigenvalue,
)

# Auto-flush print statements
print = functools.partial(print, flush=True)

####### Main functions

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
            except Exception:
                continue

            module, _ = GeneModule.objects.get_or_create(
                dataset=dataset,
                name=module_name,
            )

            GeneModuleMembership.objects.update_or_create(
                gene=gene,
                module=module,
                membership_score=membership_score,
            )


def update_gene_module_eigenvalues(file_path, species, dataset):
    try:
        dataset = Dataset.objects.get(species__scientific_name=species, name=dataset)
    except Dataset.DoesNotExist:
        print(f"Dataset not found: {species} / {dataset}")
        return

    # rows = metacells, cols = modules
    rds_obj = rds2py.read_rds(str(file_path))

    modules = rds_obj["attributes"]["names"]["data"]
    modules = [m.removeprefix("ME") for m in modules]

    metacells = rds_obj["attributes"]["row.names"]["data"]
    module_arrays = [np.array(m["data"]) for m in rds_obj["data"]]

    for m_idx, module_name in enumerate(modules):
        module, _ = GeneModule.objects.get_or_create(dataset=dataset, name=module_name)
        values = module_arrays[m_idx]

        for c_idx, eigenvalue in enumerate(values):
            metacell_name = metacells[c_idx]
            try:
                metacell = Metacell.objects.get(dataset=dataset, name=metacell_name)
            except Metacell.DoesNotExist:
                continue

            GeneModuleEigenvalue.objects.update_or_create(
                module=module,
                metacell=metacell,
                defaults={"eigenvalue": float(eigenvalue)},
            )


datasets = Dataset.objects.all()
for key in config:
    i = config[key]
    if "data_subdir" in i.keys():
        subdir = i["data_subdir"]
        dataset = i["species"]

        base_path = Path(f"{dir}/{subdir}/wgcna")
        if not base_path.exists():
            continue

        print(f"===== {dataset} =====")
        species, dataset = parse_dataset(dataset)

        wgcna_file = None
        eigenvalues_file = None

        for file in base_path.iterdir():
            if fnmatch.fnmatch(file.name.lower(), f"wgcna*{key.lower()}*.csv"):
                print("Updating gene module membership...")
                wgcna_file = file
                update_gene_modules(wgcna_file, species, dataset)

            if fnmatch.fnmatch(file.name.lower(), f"wgcna*{key.lower()}*.me.rds"):
                print("Updating gene module eigenvalues...")
                eigenvalues_file = file
                update_gene_module_eigenvalues(eigenvalues_file, species, dataset)
