#!/bin/bash

# Default env files
ENV_FILES=(--env-file ".github/super-linter.env")

# Check for 'fix' argument
for arg in "$@"; do
    if [ "$arg" == "fix" ]; then
        ENV_FILES+=(--env-file ".github/super-linter-fix.env")
    fi
done

podman run \
    -e RUN_LOCAL=true \
    -e LOG_LEVEL=WARN \
    -e SAVE_SUPER_LINTER_SUMMARY=true \
    -e SAVE_SUPER_LINTER_OUTPUT=true \
    "${ENV_FILES[@]}" \
    -v "$(pwd)":/tmp/lint \
    ghcr.io/super-linter/super-linter:latest
