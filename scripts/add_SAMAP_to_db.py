import functools
import os
import re

import pandas as pd
import yaml

# Auto-flush print statements
print = functools.partial(print, flush=True)

samap_dir = "data/raw/samap"
config_file = "data/raw/config.yaml"
verbose = False


def load_config(filename=config_file):
    with open(filename, "r") as f:
        data = yaml.safe_load(f)
    return data


def get_dataset_from_label(label):
    match = re.match(r"^(.*?)\s*\((.*?)\)$", label)
    if match:
        species = match.group(1)
        dataset = match.group(2)
    else:
        species = label
        dataset = None
    return Dataset.objects.get(species__scientific_name=species, name=dataset)


def get_metacell_types_by_dataset(filename):
    config = load_config()

    (d1, d2) = os.path.basename(filename).split(".")[0].split("-")
    if d1 not in config or d2 not in config:
        return

    s1 = d1.split("_")[0]
    s2 = d2.split("_")[0]

    d1 = get_dataset_from_label(config[d1]["species"])
    d2 = get_dataset_from_label(config[d2]["species"])

    mc1_all = {mt.name: mt for mt in d1.metacell_types.all()}
    mc2_all = {mt.name: mt for mt in d2.metacell_types.all()}

    return {s1: mc1_all, s2: mc2_all}


def add_SAMAP_scores(filename):
    mc_dict = get_metacell_types_by_dataset(filename)
    if mc_dict is None:
        return None

    df = pd.read_csv(filename, sep="\t")
    for _, (mc1, mc2, samap) in df.iterrows():
        # Ignore zero values
        samap_rounded = round(samap, 2)
        if samap_rounded == 0.00:
            continue

        (s1, mc1) = mc1.split("_", 1)
        (s2, mc2) = mc2.split("_", 1)

        if mc1 == "nan" or mc2 == "nan":
            if verbose:
                print(f'Skipping nan: mc1="{mc1}", mc2="{mc2}"')
            continue

        mc1 = mc1.replace("_", " ")
        mc2 = mc2.replace("_", " ")

        if mc1 not in mc_dict[s1]:
            if verbose:
                print(f'Skipping: mc1="{mc1}"')
            continue

        if mc2 not in mc_dict[s2]:
            if verbose:
                print(f'Skipping: mc2="{mc2}"')
            continue

        m1 = mc_dict[s1][mc1]
        m2 = mc_dict[s2][mc2]
        SAMap.objects.get_or_create(metacelltype=m1, metacelltype2=m2, samap=samap_rounded)


for f in os.listdir(samap_dir):
    filename = os.path.join(samap_dir, f)
    print(f"Adding SAMap scores from {filename}...")
    add_SAMAP_scores(filename)
