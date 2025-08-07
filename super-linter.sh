#!/bin/bash

# Defaults
ENV_FILES=(--env-file ".github/super-linter.env")
VALIDATE_ALL_CODEBASE=false
MODE=""
LOG_LEVEL="WARN"

# Valid log levels
VALID_LOG_LEVELS=(WARN INFO DEBUG ERROR NOTICE)

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
RESET='\033[0m'

# Parse Super-Linter version to use from GitHub Actions
get_linter_version() {
    local version
    local file
    file=.github/workflows/linter.yml
    version=$(grep -oE "uses:\s*super-linter/super-linter@v[0-9]+" "${file}" | head -n1 | cut -d@ -f2)

    if [[ -z "$version" ]]; then
        echo "❌ Could not determine Super-Linter version from ${file}" >&2
        exit 1
    fi

    echo "$version"
}

# Usage function
usage() {
    echo
    echo -e "${YELLOW}✨ Run Super-Linter $(get_linter_version) in check or fix mode ✨${RESET}"
    echo
    echo -e "${YELLOW}Usage:${RESET} $0 <check|fix> [--all] [--log-level=LEVEL]"
    echo
    echo -e "${YELLOW}Required:${RESET}"
    echo -e "  ${CYAN}check${RESET}                 Lint and report issues only (no changes made)"
    echo -e "  ${CYAN}fix${RESET}                   Lint and auto-fix issues where possible"
    echo
    echo -e "${YELLOW}Optional:${RESET}"
    echo -e "  ${CYAN}--changed${RESET}             Lint changed files (default)"
    echo -e "  ${CYAN}--all${RESET}                 Lint full codebase"
    echo -e "  ${CYAN}--log-level=${RESET}LEVEL     Set log level: ${CYAN}${VALID_LOG_LEVELS[*]}${RESET}"
    echo
    echo -e "${YELLOW}Examples:${RESET}"
    echo -e "  $0 check"
    echo -e "  $0 fix --all"
    echo
    exit 1
}

# Parse arguments
for arg in "$@"; do
    case "$arg" in
    --help)
        usage
        ;;
    --all)
        VALIDATE_ALL_CODEBASE=true
        ;;
    --changed)
        VALIDATE_ALL_CODEBASE=false
        ;;
    --log-level=*)
        LOG_LEVEL="${arg#*=}"
        if [[ ! " ${VALID_LOG_LEVELS[*]} " =~ ${LOG_LEVEL} ]]; then
            echo -e "❌ Invalid log level ${RED}$LOG_LEVEL${RESET}!"
            echo -e "Accepted values are: ${CYAN}${VALID_LOG_LEVELS[*]}${RESET}"
            exit 1
        fi
        ;;
    fix)
        MODE="fix"
        ENV_FILES+=(--env-file ".github/super-linter-fix.env")
        ;;
    check)
        MODE="check"
        ;;
    *)
        usage
        ;;
    esac
done

# Ensure mode is set
[[ -z "$MODE" ]] && usage

podman run \
    "${ENV_FILES[@]}" \
    -e RUN_LOCAL=true \
    -e LOG_LEVEL="$LOG_LEVEL" \
    -e SAVE_SUPER_LINTER_SUMMARY=true \
    -e SAVE_SUPER_LINTER_OUTPUT=true \
    -e VALIDATE_ALL_CODEBASE="$VALIDATE_ALL_CODEBASE" \
    -v "$(pwd)":/tmp/lint \
    --platform linux/amd64 \
    ghcr.io/super-linter/super-linter:"$(get_linter_version)"

# Print summary results
echo
echo -e "✨ ${YELLOW}Super-Linter has finished!${RESET} ✨"
echo
cat super-linter-output/super-linter-summary.md
