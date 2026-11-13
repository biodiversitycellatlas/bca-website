#!/bin/sh

if [ -n "$SLURM_JOB_ID" ]; then echo "✅ In Slurm job: $SLURM_JOB_ID"; else echo "❌ Not in Slurm job — get an interactive session!"; fi

# 1. Activate the venv
source .venv/bin/activate

# 2. Load .env into your current shell
set -a
source .env
set +a
