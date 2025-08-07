#!/bin/bash
set -e

YELLOW='\033[1;33m'
CYAN='\033[1;36m'
RESET='\033[0m'

# Usage function
usage() {
    echo
    echo -e "${YELLOW}✨ Run Super-linter in check or fix mode ✨${RESET}"
    echo
    echo -e "${YELLOW}Usage:${RESET} $0 <check|fix> [--all]"
    echo
    echo -e "${YELLOW}Required:${RESET}"
    echo -e "  ${CYAN}check${RESET}       Lint and report issues only (no changes made)"
    echo -e "  ${CYAN}fix${RESET}         Lint and auto-fix issues where possible"
    echo
    echo -e "${YELLOW}Optional:${RESET}"
    echo -e "  ${CYAN}--changed${RESET}   Lint changed files (default)"
    echo -e "  ${CYAN}--all${RESET}       Lint full codebase"
    echo
    echo -e "${YELLOW}Examples:${RESET}"
    echo -e "  $0 check"
    echo -e "  $0 fix --all"
    echo
    exit 1
}

# Defaults
ENV_FILES=(--env-file ".github/super-linter.env")
VALIDATE_ALL_CODEBASE=false
MODE=""

# Parse args
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
    -e LOG_LEVEL=WARN \
    -e SAVE_SUPER_LINTER_SUMMARY=true \
    -e SAVE_SUPER_LINTER_OUTPUT=true \
    -e VALIDATE_ALL_CODEBASE="$VALIDATE_ALL_CODEBASE" \
    -v "$(pwd)":/tmp/lint \
    ghcr.io/super-linter/super-linter:latest

echo
echo -e "✨ ${YELLOW}Super-linter has finished!${RESET} ✨"
echo
cat super-linter-output/super-linter-summary.md
