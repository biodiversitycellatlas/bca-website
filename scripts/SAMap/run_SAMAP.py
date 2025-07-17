#!/usr/bin python3
"""
Run SAMAP to perform pairwise comparisons among the specified species.
"""

import functools
import os
import sys

import yaml

try:
    import numpy as np
    import pandas as pd
    from rds2py import read_rds
    from samalg import SAM
    from samap.mapping import SAMAP
    from samap.utils import load_samap, save_samap
except ImportError:
    print("Error: Missing dependencies. Did you forget to run `conda activate SAMap`?")
    sys.exit(1)

# Auto-flush print statements
print = functools.partial(print, flush=True)

script_name = os.path.basename(__file__)

# Global variables ============================================================
dir = "SAMap"
alignment_dir = f"{dir}/blast/"
sam_dir = f"{dir}/sam/"
samap_dir = f"{dir}/samap"
config_file = "config.yaml"

# Script ======================================================================


def get_config_filepaths(species):
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    species_data = data.get(species, {})
    subdir = species_data.get("data_subdir", "")

    files = [
        species_data.get(e) for e in ("umicountsc_file", "cellmc_file", "ann_file")
    ]
    return [os.path.join(subdir, f) for f in files]


def prepare_cell_types(cellmc_file, ann_file):
    # Get metacell types
    ann_df = pd.read_csv(ann_file, sep="\t")
    metacell_types = ann_df.set_index("metacell")["cell_type"]

    # Assign metacell type directly to each cell
    cellmc_rds = read_rds(cellmc_file)
    cells = list(cellmc_rds.names)
    metacells = list(cellmc_rds)

    cell_types = {}
    for cell, metacell in zip(cells, metacells):
        cell_types[cell] = metacell_types.get(metacell + 1, None)
    return cell_types


def save_SAM_file(dataset, sam_dir):
    print(f"Reading counts matrix for {dataset}...")
    (counts_file, cellmc_file, ann_file) = get_config_filepaths(dataset)
    rds = read_rds(counts_file)

    counts = rds.matrix.T
    genes = np.array(rds.dimnames[0])
    cells = np.array(rds.dimnames[1])

    print("Preparing SAM object...")
    sam = SAM(counts=(counts, genes, cells))
    sam.preprocess_data()

    print("Running SAM...")
    sam.run()

    print("Adding cell types to SAM object...")
    cell_types = prepare_cell_types(cellmc_file, ann_file)
    cell_types_map = [
        cell_types.get(cell, "unannotated") for cell in sam.adata.obs.index
    ]
    sam.adata.obs["cell"] = sam.adata.obs.index
    sam.adata.obs["celltype"] = cell_types_map

    print("Saving SAM results...")
    filename = f"{sam_dir}/{dataset}.h5ad"
    os.makedirs(sam_dir, exist_ok=True)
    sam.save_anndata(filename)
    print("Finished!")
    return filename


def run_pairwise_SAMAP(d1, d2, sam_dir, alignment_dir, samap_dir):
    sam1 = SAM().load_data(f"{sam_dir}/{d1}.h5ad")
    sam2 = SAM().load_data(f"{sam_dir}/{d2}.h5ad")

    # Use species here to get the right alignment map
    s1 = d1.split("_")[0]
    s2 = d2.split("_")[0]

    if s1 == s2:
        print(f"Error: {d1} and {d2} share the same species ({species}), aborting!")
        sys.exit(1)

    params = {s1: sam1, s2: sam2}
    keys = {s1: "celltype", s2: "celltype"}

    print("Initialising SAMAP...")
    sm = SAMAP(params, keys=keys, f_maps=alignment_dir)

    print("Running SAMAP...")
    sm.run()

    print("Saving SAMAP results...")
    os.makedirs(samap_dir, exist_ok=True)
    save_samap(sm, f"{samap_dir}/{d1}-{d2}.samap")

    print(f"Saving pairwise scores between cell types from {s1} and {s2}...")
    # D: highest-scoring alignment scores for each cell type
    # MappingTable: pairwise mapping scores between cell types
    D, MappingTable = get_mapping_scores(sm, keys)

    # Keep upper diagonal only
    mask = np.triu(np.ones(MappingTable.shape), k=1).astype(bool)
    MappingTable_upper = MappingTable.where(mask)

    # Convert matrix to long format
    df = MappingTable_upper.reset_index().melt(id_vars="index")

    # Filter zero/missing values and convert to percentage
    df = df.query("value != 0").dropna()
    df["value"] = df["value"] * 100

    out_name = f"{os.path.splitext(filename)[0]}_mapping.tsv"
    df.to_csv(out_name, sep="\t", index=False)

    print("Finished!")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "sam":
        dataset = sys.argv[2]
        save_SAM_file(dataset, sam_dir)
    elif len(sys.argv) == 4 and sys.argv[1] == "samap":
        d1, d2 = sys.argv[2], sys.argv[3]
        run_pairwise_SAMAP(d1, d2, sam_dir, alignment_dir, samap_dir)
    else:
        print("Error: Invalid arguments")
        print("Usage:")
        print("  python {script_name} sam <dataset>")
        print("  python {script_name} samap <dataset1> <dataset2>")
        sys.exit(1)
