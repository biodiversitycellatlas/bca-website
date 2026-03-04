#!/usr/bin/env python3

import csv
import fnmatch
import functools
import os
from pathlib import Path

from scripts.utils import load_config, parse_dataset
from app.models import GeneList, Species

# Auto-flush print statements
print = functools.partial(print, flush=True)

# Main functions

config = load_config("data/raw/config.yaml")
data_dir = "data/raw"
lists_dir = f"{data_dir}/gene_lists"

gene_list_map = {
    "chr": "Chromatin",
    "ion": "Ion channels",
    "neu": "Neural",
    "sig": "Signalling",
    "rbp": "RNA-binding proteins",
    "tfs": "Transcription factors",
    "myo": "Myosins",
}
gene_list_map = {acronym: GeneList.objects.get(name=name) for acronym, name in gene_list_map.items()}


def update_gene_modules(file_path, species, gene_list):
    with open(file_path) as file_path:
        reader = csv.DictReader(file_path, delimiter="\t")

        # Avoid adding same genes to gene list
        existing_genes = set(gene_list.genes.all())

        g_list = list()
        for gene in reader:
            gene = list(gene.values())[0]

            if gene in existing_genes:
                continue

            try:
                g = species.genes.get(name=gene)
                g_list.append(g)
            except species.genes.model.DoesNotExist:
                print(f"Warning: {gene} has no match in {species}")
                continue

        gene_list.genes.add(*g_list)
    return True


all_species = Species.objects.all()

tf_files = []

for key in config:
    i = config[key]
    key = key.split("_")[0]  # only need the species part
    if "species" not in i.keys():
        continue
    species, dataset = parse_dataset(i["species"])

    try:
        species = Species.objects.get(scientific_name=species)
    except Species.DoesNotExist:
        print(f"Warning: species {species} not found")
        continue

    base_path = Path(lists_dir)
    for file in base_path.iterdir():
        if fnmatch.fnmatch(file.name.lower(), f"*{key.lower()}*.txt"):
            print(f"===== {key}: {file} =====")

            # Get gene list from file name
            acronym = os.path.basename(file.name).split(".")[0]
            gene_list = gene_list_map[acronym]
            print(gene_list)

            update_gene_modules(file, species, gene_list)

    if "tf_annot_file" in i.keys():
        path = os.path.join(data_dir, i["data_subdir"], i["tf_annot_file"])
        tf_files.append((species, path))

for f in tf_files:
    species, file = f
    update_gene_modules(file, species, gene_list_map["tfs"])
