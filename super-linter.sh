#!/bin/bash

# Check for --fix flag
for arg in "$@"; do
    if [ "$arg" == "fix" ]; then
        FIX_ENV="--env-file .github/super-linter-fix.env"
    fi
done

podman run \
    -e RUN_LOCAL=true \
    -e LOG_LEVEL=WARN \
    -e SAVE_SUPER_LINTER_SUMMARY=true \
    -e SAVE_SUPER_LINTER_OUTPUT=true \
    --env-file ".github/super-linter.env" \
    ${FIX_ENV} \
    -v $(pwd):/tmp/lint \
    ghcr.io/super-linter/super-linter:latest
