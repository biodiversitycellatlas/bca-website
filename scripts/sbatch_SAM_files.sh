#!/bin/bash

export CONDA=$HOME/.local/miniforge3

species_list=(
    mmus aque_adult aque_larva cele chem hhon hoi23 hvul
    mlei nvec sman smed spis_coral spis_larva spis_polyp
    spol tadh trh2 xesp
)

mkdir -p logs

for species in "${species_list[@]}"; do
    sbatch --job-name="sam_${species}" --time=00:30:00 --mem=16GB \
    	--output="logs/sam_${species}_%j.out" \
        --wrap="source ${CONDA}/etc/profile.d/conda.sh && conda activate SAMap && python run_SAMAP.py sam $species"
done
