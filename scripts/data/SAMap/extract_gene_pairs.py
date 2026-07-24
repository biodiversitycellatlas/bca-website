#!/usr/bin/env python3

import argparse
import pickle

YELLOW = "\033[93m"
RESET = "\033[0m"

def status(msg, color=YELLOW):
        print(f"{color}[STATUS]{RESET} {msg}")
    
status("Loading libraries...")
from samap.analysis import GenePairFinder

# Parse CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument("infile", help="Input SAMap .pkl file")
args = parser.parse_args()

outfile = args.infile.replace(".samap.pkl", ".gene_pairs.pkl")

# Load the SAMap object
status(f"Loading {args.infile}...")
with open(args.infile, "rb") as f:
        sm = pickle.load(f)
    
# Find all gene pairs
status("Finding gene pairs...")
species = list(sm.sams.keys())
gpf = GenePairFinder(
        sm,
        keys={species[0]: "celltype", species[1]: "celltype"}
)
gene_pairs = gpf.find_all(align_thr=0.2)

# Save the gene pairs
status(f"Saving {outfile}...")
with open(outfile, "wb") as f:
        pickle.dump(gene_pairs, f)
    
status("Done!")
