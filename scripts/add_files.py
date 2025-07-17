#!/usr/bin/env python3

from pathlib import Path
import fnmatch
import os
import functools
from scripts.utils import load_config, parse_dataset
from django.core.files import File as DjangoFile

# Auto-flush print statements
print = functools.partial(print, flush=True)

####### Main functions

config = load_config("data/raw/config.yaml")
dir = "data/raw/files"


def add_file(file_path, species):
    file_path = str(file_path)
    if file_path.endswith(".dmnd"):
        type = "DIAMOND"
    elif file_path.endswith(".fasta") or file_path.endswith(".fa"):
        type = "Proteome"
    else:
        return

    with open(file_path, "rb") as f:
        django_file = DjangoFile(f, name=os.path.basename(file_path))
        File.objects.get_or_create(
            species=species, type=type, defaults={"file": django_file}
        )

    return True


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

    base_path = Path(dir)
    for file in base_path.iterdir():
        if fnmatch.fnmatch(file.name.lower(), f"{key.lower()}*"):
            print(f"===== {key}: {file} =====")
            add_file(file, species)
