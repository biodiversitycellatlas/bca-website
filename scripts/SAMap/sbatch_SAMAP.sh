#!/bin/bash

export CONDA=$HOME/.local/miniforge3
mkdir -p logs/samap

datasets=(
    mmus aque_adult aque_larva cele chem hhon hoi23 hvul
    mlei nvec sman smed spis_coral spis_larva spis_polyp
    spol tadh trh2 xesp
)

# Create all pairs of species (without repetition)
pairs=()
for ((i=0; i<${#datasets[@]}-1; i++)); do
    for ((j=i+1; j<${#datasets[@]}; j++)); do
        pairs+=("${datasets[i]}+${datasets[j]}")
    done
done

# Custom pairs
#pairs=(
#    "mmus+aque_adult"
#    "smed+spis_larva"
#)

# Submit jobs for each pair
for pair in "${pairs[@]}"; do
    d1=${pair%%+*}
    d2=${pair##*+}
    sbatch --job-name="samap_${d1}_${d2}" \
           --output="logs/samap/${d1}-${d2}-%j.out" \
           --time=05:00:00 \
           --mem=16G \
           --wrap="source ${CONDA}/etc/profile.d/conda.sh && conda activate SAMap && python run_SAMAP.py samap $d1 $d2"
done
