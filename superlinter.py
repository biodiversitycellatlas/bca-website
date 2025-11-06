#!/usr/bin/env python3
"""
Run Super-Linter via Podman with flexible environment and mode options.

Supports 'check' and 'fix' modes, selective validators and log levels.

Environment variables are read from .github/linters/super-linter.env and
.github/linters/super-linter-fix.env as needed.

Usage:
  super-linter.py <check|fix> [--all] [--log-level=LEVEL] [linters]
"""

import os
import sys
import re
import subprocess
from pathlib import Path

# Defaults
ENV_DIR = ".github/linters"
ENV_CHECK = f"{ENV_DIR}/super-linter.env"
ENV_FIX = f"{ENV_DIR}/super-linter-fix.env"

ENV_FILES = [ENV_CHECK]
VALID_LOG_LEVELS = {"WARN", "INFO", "DEBUG", "ERROR", "NOTICE"}

# Colors
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[1;36m"
RESET = "\033[0m"


VALIDATOR_FLAGS = {
    "--python": [
        "PYTHON_PYLINT",
        "PYTHON_BLACK",
        "PYTHON_FLAKE8",
        "PYTHON_RUFF",
        "PYTHON_RUFF_FORMAT",
    ],
    "--pylint": ["PYTHON_PYLINT"],
    "--black": ["PYTHON_BLACK"],
    "--flake8": ["PYTHON_FLAKE8"],
    "--ruff": ["PYTHON_RUFF", "PYTHON_RUFF_FORMAT"],
    "--r": ["R"],
    "--github": ["GITHUB_ACTIONS", "GITHUB_ACTIONS_ZIZMOR"],
    "--zizmor": ["GITHUB_ACTIONS_ZIZMOR"],
    "--javascript": ["JAVASCRIPT_ES", "JAVASCRIPT_PRETTIER"],
    "--javascript-es": ["JAVASCRIPT_ES"],
    "--javascript-prettier": ["JAVASCRIPT_PRETTIER"],
}

# shortcuts
VALIDATOR_FLAGS["--py"] = VALIDATOR_FLAGS["--python"]
VALIDATOR_FLAGS["--js"] = VALIDATOR_FLAGS["--javascript"]
VALIDATOR_FLAGS["--gh"] = VALIDATOR_FLAGS["--github"]

def get_linter_version():
    """Get Super-Linter version from GitHub Actions workflows."""

    file = Path(".github/workflows/linter.yml")
    if not file.exists():
        print(f"{RED}❌ Could not find {file}{RESET}", file=sys.stderr)
        sys.exit(1)

    with file.open(encoding="utf-8") as f:
        for line in f:
            m = re.search(r"uses:\s*super-linter/super-linter@(v[\d.]+)", line)
            if m:
                return m.group(1)
    print(
        f"{RED}❌ Could not determine Super-Linter version from {file}{RESET}",
        file=sys.stderr,
    )
    sys.exit(1)


def usage():
    """Script usage instructions."""

    print(
        f"""
✨ {YELLOW}Run Super-Linter {get_linter_version()} in check or fix mode{RESET} ✨

{YELLOW}Usage:{RESET} {sys.argv[0]} <check|fix> [--all] [--log-level=LEVEL]

{YELLOW}Required:{RESET}
  {CYAN}check{RESET}                 Lint and report issues only (no changes made)
  {CYAN}fix{RESET}                   Lint and auto-fix issues where possible

{YELLOW}Optional:{RESET}
  {CYAN}--changed{RESET}             Lint changed files (default)
  {CYAN}--all{RESET}                 Lint full codebase
  {CYAN}--log-level=LEVEL{RESET}     Set log level: {", ".join(VALID_LOG_LEVELS)}

{YELLOW}Validator flags:{RESET}
  {CYAN}--py, --python{RESET}        Enable all Python linters
  {CYAN}--pylint{RESET}              Enable Pylint
  {CYAN}--black{RESET}               Enable Black
  {CYAN}--flake8{RESET}              Enable Flake8
  {CYAN}--ruff{RESET}                Enable Ruff

  {CYAN}--gh, --github{RESET}        Enable all GitHub Actions linters
  {CYAN}--zizmor{RESET}              Enable Zizmor

  {CYAN}--js, --javascript{RESET}    Enable all JavaScript linters
  {CYAN}--javascript-prettier{RESET} Enable JavaScript Prettier
  {CYAN}--javascript-es{RESET}       Enable JavaScript ES

  {CYAN}--r{RESET}                   Enable R linter

{YELLOW}Examples:{RESET}
  {CYAN}{sys.argv[0]} check{RESET}
  {CYAN}{sys.argv[0]} fix --all{RESET}
"""
    )
    sys.exit(1)


def parse_env_file(file):
    """
    Parse environment variables from a file.

    Args:
        file (str or Path): Path to the environment file.

    Returns:
        dict: Environment variables as key-value pairs.
    """

    env_vars = {}
    path = Path(file)
    if not path.exists():
        return env_vars
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip()
    return env_vars


def disable_validators(env_files):
    """
    Disable all linters.

    Args:
        env_files (list): List of environment file paths.
        mode (str, optional): Mode to determine if disabling should occur. Defaults to None.

    Returns:
        dict: Environment variables with validators disabled.
    """

    env = {}
    for file in env_files:
        env.update(parse_env_file(file))

    # Override VALIDATE_* except VALIDATE_ALL_CODEBASE to false
    for k in list(env.keys()):
        if k.startswith("VALIDATE_") and k != "VALIDATE_ALL_CODEBASE":
            del env[k]
        elif k.startswith("FIX_"):
            del env[k]

    return env


def enable_validator(keys, env_vars, mode=None):
    """
    Enable a specific validator and (if mode='fix') its fix option.

    Args:
        key (list): List of validator keys (e.g., ["PYTHON_PYLINT"]).
        env_vars (dict): Environment variables dictionary to update.
        mode (str, optional): Current mode, enables FIX if "fix".

    Returns:
        dict: Updated environment variables with validator enabled.
    """
    for key in keys:
        env_vars["VALIDATE_" + key] = "true"
        if mode == "fix":
            env_vars["FIX_" + key] = "true"
    return env_vars


def parse_args(args):
    """
    Parse command-line arguments to set variables for Super-Linter run.

    Args:
        args (list): List of command-line arguments.

    Returns:
        tuple: (env_files (list), env_vars (dict)) for environment configuration.
    """

    mode = None
    validate_all_codebase = False
    log_level = "WARN"
    env_files = ENV_FILES.copy()
    env_vars = {}

    positional = [a for a in args if not a.startswith("--")]
    options = [a for a in args if a.startswith("--")]
    sorted_args = positional + options

    validators_disabled = False
    for arg in sorted_args:
        if arg == "fix":
            mode = "fix"
            env_files.append(ENV_FIX)
        elif arg == "check":
            mode = "check"
        elif arg == "--all":
            validate_all_codebase = True
        elif arg == "--changed":
            validate_all_codebase = False
        elif arg.startswith("--log-level="):
            level = arg.split("=", 1)[1].upper()
            if level not in VALID_LOG_LEVELS:
                print(f"❌ Invalid log level {RED}{level}{RESET}!")
                print(f"Accepted values are: {CYAN}{' '.join(VALID_LOG_LEVELS)}{RESET}")
                sys.exit(1)
            log_level = level
        elif arg == "--help":
            usage()
        elif arg in VALIDATOR_FLAGS:
            if not validators_disabled:
                env_vars = disable_validators(env_files)
                validators_disabled = True
            env_vars = enable_validator(VALIDATOR_FLAGS[arg], env_vars, mode=mode)
            env_files = []
        else:
            usage()

    if not mode:
        usage()

    # Add fixed environment variables
    env_vars.update(
        {
            "RUN_LOCAL": "true",
            "LOG_LEVEL": log_level,
            "SAVE_SUPER_LINTER_SUMMARY": "true",
            "SAVE_SUPER_LINTER_OUTPUT": "true",
            "VALIDATE_ALL_CODEBASE": "true" if validate_all_codebase else "false",
        }
    )

    return env_files, env_vars


def run_linters(env_files, env_vars):
    """
    Build and execute the Podman command to run Super-Linter.

    Args:
        env_files (list): List of environment file paths.
        env_vars (dict): Dictionary of environment variables.

    Prints:
        Full Podman command and contents of the Super-Linter summary file.
    """

    env_list = []

    if env_files:
        for file in env_files:
            env_list.extend([f"--env-file={file}"])

    for k, v in env_vars.items():
        env_list.append(f"-e {k}={v}")

    cmd = [
        "time",
        "podman",
        "run",
        *env_list,
        "-v",
        f"{os.getcwd()}:/tmp/lint",
        "--platform",
        "linux/amd64",
        "--pull",
        "newer",
        f"ghcr.io/super-linter/super-linter:{get_linter_version()}",
    ]

    print(f"\n✨{YELLOW} Running Super-Linter command {RESET}✨")
    print(CYAN + " ".join(cmd) + RESET + "\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        pass  # ignore error

    print(f"\n✨ {YELLOW}Super-Linter has finished!{RESET} ✨\n")

    summary_file = Path("super-linter-output/super-linter-summary.md")
    if summary_file.exists():
        print(summary_file.read_text(encoding="utf-8"))


def main():
    """Prepare environment, run Super-Linter via Podman, and print summary."""
    args = sys.argv[1:]
    env_files, env_vars = parse_args(args)
    run_linters(env_files, env_vars)


if __name__ == "__main__":
    main()
