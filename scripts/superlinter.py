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
import argparse

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

VALIDATORS = {
    "python": {
        "flags": ("--python", "--py"),
        "env": ["PYTHON_PYLINT", "PYTHON_BLACK", "PYTHON_FLAKE8", "PYTHON_RUFF", "PYTHON_RUFF_FORMAT"],
        "category": "Python",
        "help": "Enable all Python linters",
    },
    "pylint": {
        "flags": "--pylint",
        "env": ["PYTHON_PYLINT"],
        "category": "Python",
        "help": "Enable Pylint",
    },
    "black": {
        "flags": "--black",
        "env": ["PYTHON_BLACK"],
        "category": "Python",
        "help": "Enable Black",
    },
    "flake8": {
        "flags": "--flake8",
        "env": ["PYTHON_FLAKE8"],
        "category": "Python",
        "help": "Enable Flake8",
    },
    "ruff": {
        "flags": "--ruff",
        "env": ["PYTHON_RUFF", "PYTHON_RUFF_FORMAT"],
        "category": "Python",
        "help": "Enable Ruff",
    },
    "r": {
        "flags": "--r",
        "env": ["R"],
        "category": "R",
        "help": "Enable R linter",
    },
    "github": {
        "flags": ("--github", "--gh"),
        "env": ["GITHUB_ACTIONS", "GITHUB_ACTIONS_ZIZMOR"],
        "category": "GitHub",
        "help": "Enable all GitHub Actions linters",
    },
    "zizmor": {
        "flags": "--zizmor",
        "env": ["GITHUB_ACTIONS_ZIZMOR"],
        "category": "GitHub",
        "help": "Enable Zizmor",
    },
    "javascript": {
        "flags": ("--javascript", "--js"),
        "env": ["JAVASCRIPT_ES", "JAVASCRIPT_PRETTIER"],
        "category": "JavaScript",
        "help": "Enable all JavaScript linters",
    },
    "javascript-es": {
        "flags": "--javascript-es",
        "env": ["JAVASCRIPT_ES"],
        "category": "JavaScript",
        "help": "Enable JavaScript ES",
    },
    "javascript-prettier": {
        "flags": "--javascript-prettier",
        "env": ["JAVASCRIPT_PRETTIER"],
        "category": "JavaScript",
        "help": "Enable JavaScript Prettier",
    },
}


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


def parse_args():
    """
    Parse command-line arguments to set variables for Super-Linter run.

    Args:
        args (list): List of command-line arguments.

    Returns:
        tuple: (env_files (list), env_vars (dict)) for environment configuration.
    """
    parser = argparse.ArgumentParser(description=f"Run Super-Linter {get_linter_version()} in check or fix mode")
    parser.add_argument("mode", choices=["check", "fix"], help="check or fix mode")
    parser.add_argument("--all", action="store_true", help="Lint full codebase")
    parser.add_argument("--changed", action="store_true", help="Lint changed files only (default)")
    parser.add_argument("--log-level", choices=VALID_LOG_LEVELS, default="WARN", help="Set log level")

    # Create groups of linters
    groups = {}
    for category in sorted({v["category"] for v in VALIDATORS.values()}):
        groups[category] = parser.add_argument_group(f"{category} linters")

    for key, v in VALIDATORS.items():
        flags = v["flags"]
        if isinstance(flags, str):
            flags = [flags]

        groups[v["category"]].add_argument(
            *flags, dest="validators", action="append_const", const=key, help=v["help"], default=[]
        )

    args = parser.parse_args()
    return args


def prepare_env(args):
    env_files = ENV_FILES.copy()
    env_vars = {}
    mode = args.mode

    if mode == "fix":
        env_files.append(ENV_FIX)

    validators_disabled = False
    for v in args.validators:
        if not validators_disabled:
            env_vars = disable_validators(env_files)
            validators_disabled = True
        flags = VALIDATORS[v]["env"]
        env_vars = enable_validator(flags, env_vars, mode=args.mode)
        env_files = []

    # Add fixed environment variables
    env_vars.update(
        {
            "RUN_LOCAL": "true",
            "LOG_LEVEL": args.log_level,
            "SAVE_SUPER_LINTER_SUMMARY": "true",
            "SAVE_SUPER_LINTER_OUTPUT": "true",
            "VALIDATE_ALL_CODEBASE": "true" if args.all else "false",
        }
    )

    return env_files, env_vars


def prepare_linter_cmd(env_files, env_vars):
    """
    Build Podman command to run Super-Linter based on environment variables.

    Args:
        env_files (list): List of environment file paths.
        env_vars (dict): Dictionary of environment variables.

    Prints:
        Full Podman command.
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
    return cmd


def run_linters(env_files, env_vars):
    """
    Build and execute the Podman command to run Super-Linter.

    Args:
        env_files (list): List of environment file paths.
        env_vars (dict): Dictionary of environment variables.

    Prints:
        Full Podman command and contents of the Super-Linter summary file.
    """

    print(f"\n✨{YELLOW} Running Super-Linter {get_linter_version()} {RESET}✨")
    cmd = prepare_linter_cmd(env_files, env_vars)
    print(CYAN + " ".join(cmd) + RESET + "\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        pass  # ignore error

    print(f"\n✨ {YELLOW}Super-Linter has finished!{RESET} ✨\n")


def print_summary_table(filename):
    """Print summary table."""
    summary_file = Path(filename)
    if summary_file.exists():
        content = summary_file.read_text(encoding="utf-8")

        # Find summary table start and end
        table_start = content.find("| ")
        table_lines = content[table_start:].splitlines()
        table_only = []
        for line in table_lines:
            if line.startswith("| "):
                table_only.append(line)
            else:
                break
        print("\n".join(table_only), "\n")


def main():
    """Prepare environment, run Super-Linter via Podman, and print summary table."""
    args = sys.argv[1:]
    args = parse_args()
    env_files, env_vars = prepare_env(args)
    run_linters(env_files, env_vars)
    print_summary_table("super-linter-output/super-linter-summary.md")


if __name__ == "__main__":
    main()
