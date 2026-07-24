#!/bin/bash
#SBATCH --job-name=samap_genepairs
#SBATCH --output=logs/%x.%j.out
#SBATCH --error=logs/%x.%j.err
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G

module purge
module load Python/3.10

if [[ $# -ne 1 ]]; then
    echo "Usage: sbatch run_genepairs.sh <samap.pkl>"
    exit 1
fi
    
if [[ ! -f "$1" ]]; then
    echo "Error: input file '$1' does not exist."
    exit 1
fi
    
python3 extract_gene_pairs.py "$1"
