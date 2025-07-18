#!/bin/bash
set -euo pipefail

species=(aque hoih23 mmus smed tadh xesp chem dmel hvul nvec spis cele hhon mlei sman spol trh2)
n_threads=8 # adjust as needed
config=config.yaml

blast_dir=blast
mkdir -p ${blast_dir}

get_config_fasta() {
    local s=$1
    awk -v sp="$s" '
        $0 ~ "^"sp"[ _a-zA-Z0-9-]* *:$" {flag=1; next}
        /^[^ ]/ {flag=0}
        flag && /data_subdir:/ {subdir=$2}
        flag && /fasta_file:/ {
            print subdir "/" $2
            exit
        }
        ' "$config"
}

submit_blastp() {
    local query=$1
    local db=$2
    local out_file=$3

    local image="$HOME/.local/images/blast_2.16.0.sif"
    local job
    job=blast_$(basename "$out_file" .txt)
    local out_log="${out_file%.txt}.out"

    local email=nuno.agostinho@crg.eu

    sbatch --time=00:20:00 --job-name="$job" --cpus-per-task=$n_threads \
        --output="${out_log}" --mail-type=END,FAIL --mail-user=$email \
        --wrap="apptainer exec $image blastp -query $query -db $db -outfmt 6 -out ${out_file} -num_threads $n_threads -max_hsps 1 -evalue 1e-6"
}

for ((i = 0; i < ${#species[@]}; i++)); do
    for ((j = i + 1; j < ${#species[@]}; j++)); do
        s1=${species[i]}
        s2=${species[j]}

        out_dir="${blast_dir}/${s1}${s2}"
        mkdir -p "${out_dir}"

        pr1=$(get_config_fasta "$s1")
        pr2=$(get_config_fasta "$s2")

        submit_blastp "$pr1" "$pr2" "${out_dir}/${s1}_to_${s2}.txt"
        submit_blastp "$pr2" "$pr1" "${out_dir}/${s2}_to_${s1}.txt"
        echo
    done
done
