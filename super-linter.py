#!/usr/bin/env python3
import os
import sys
import re
import subprocess
from pathlib import Path

# Defaults
ENV_FILES = [".github/super-linter.env"]
VALIDATE_ALL_CODEBASE = False
MODE = None
LOG_LEVEL = "WARN"
VALID_LOG_LEVELS = {"WARN", "INFO", "DEBUG", "ERROR", "NOTICE"}

# Colors
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
CYAN = '\033[1;36m'
RESET = '\033[0m'

def get_linter_version():
    file = Path(".github/workflows/linter.yml")
    if not file.exists():
        print(f"{RED}❌ Could not find {file}{RESET}", file=sys.stderr)
        sys.exit(1)

    with file.open() as f:
        for line in f:
            m = re.search(r"uses:\s*super-linter/super-linter@v(\d+)", line)
            if m:
                return f"v{m.group(1)}"
    print(
        f"{RED}❌ Could not determine Super-Linter version from {file}{RESET}",
        file=sys.stderr)
    sys.exit(1)

def usage():
    print(f"""
✨ {YELLOW} Run Super-Linter {get_linter_version()} in check or fix mode {RESET} ✨

{YELLOW}Usage:{RESET} {sys.argv[0]} <check|fix> [--all] [--log-level=LEVEL]

{YELLOW}Required:{RESET}
  {CYAN}check{RESET}                 Lint and report issues only (no changes made)
  {CYAN}fix{RESET}                   Lint and auto-fix issues where possible

{YELLOW}Optional:{RESET}
  {CYAN}--changed{RESET}             Lint changed files (default)
  {CYAN}--all{RESET}                 Lint full codebase
  {CYAN}--log-level=LEVEL{RESET}     Set log level: {', '.join(VALID_LOG_LEVELS)}

{YELLOW}Examples:{RESET}
  {CYAN}{sys.argv[0]} check{RESET}
  {CYAN}{sys.argv[0]} fix --all{RESET}
""")
    sys.exit(1)

def parse_env_file(file):
    vars = {}
    path = Path(file)
    if not path.exists():
        return vars
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            vars[key.strip()] = val.strip()
    return vars

def disable_validators(env_files, mode=None):
    if mode is None:
        return None

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

def enable_validator(key, env_vars, mode=None):
    env_vars["VALIDATE_" + key] = "true"
    if mode is not None and mode == "fix":
        env_vars["FIX_" + key] = "true"
    return env_vars

def main():
    global MODE, VALIDATE_ALL_CODEBASE, LOG_LEVEL

    args = sys.argv[1:]
    positional = [a for a in args if not a.startswith("--")]
    options = [a for a in args if a.startswith("--")]

    # Sort: positional first, then options
    sorted_args = positional + options

    env_files = ENV_FILES.copy()
    env_vars = {}

    for arg in sorted_args:
        if arg == "fix":
            MODE = "fix"
            env_files.append(".github/super-linter-fix.env")
        elif arg == "check":
            MODE = "check"
        elif arg == "--all":
            VALIDATE_ALL_CODEBASE = True
        elif arg == "--changed":
            VALIDATE_ALL_CODEBASE = False
        elif arg.startswith("--log-level="):
            level = arg.split("=",1)[1].upper()
            if level not in VALID_LOG_LEVELS:
                print(f"❌ Invalid log level {RED}{level}{RESET}!")
                print(f"Accepted values are: {CYAN}{' '.join(VALID_LOG_LEVELS)}{RESET}")
                sys.exit(1)
            LOG_LEVEL = level
        elif arg == "--help":
            usage()
        elif arg == "--pylint":
            env_vars = disable_validators(env_files, mode=MODE)
            env_vars = enable_validator("PYTHON_PYLINT", env_vars, mode=MODE)
            env_files = []
        elif arg == "--black":
            env_vars = disable_validators(env_files, mode=MODE)
            env_vars = enable_validator("PYTHON_BLACK", env_vars, mode=MODE)
            env_files = []
        elif arg == "--flake8":
            env_vars = disable_validators(env_files, mode=MODE)
            env_vars = enable_validator("PYTHON_FLAKE8", env_vars, mode=MODE)
            env_files = []
        elif arg == "--ruff":
            env_vars = disable_validators(env_files, mode=MODE)
            env_vars = enable_validator("PYTHON_RUFF", env_vars, mode=MODE)
            env_files = []
        else:
            usage()

    if not MODE:
        usage()

    # Compose environment variables for podman
    env_list = []
    # Add environment files vars if still used
    if env_files:
        for file in env_files:
            env_list.extend([f"--env-file={file}"])

    # Add explicit env vars from env_vars dict
    for k, v in env_vars.items():
        env_list.append(f"-e {k}={v}")

    # Add fixed env vars
    env_list.extend([
        "-e RUN_LOCAL=true",
        f"-e LOG_LEVEL={LOG_LEVEL}",
        "-e SAVE_SUPER_LINTER_SUMMARY=true",
        "-e SAVE_SUPER_LINTER_OUTPUT=true",
        f"-e VALIDATE_ALL_CODEBASE={'true' if VALIDATE_ALL_CODEBASE else 'false'}"
    ])

    podman_cmd = [
        "podman", "run",
        *env_list,
        "-v", f"{os.getcwd()}:/tmp/lint",
        "--platform", "linux/amd64",
        f"ghcr.io/super-linter/super-linter:{get_linter_version()}"
    ]

    print(f"\n✨{YELLOW} Super-Linter command running {RESET}✨")
    print("" + CYAN + " ".join(podman_cmd) + RESET + "\n")

    try:
        subprocess.run(podman_cmd, check=True)
    except subprocess.CalledProcessError:
        pass  # ignore error

    print(f"\n✨ {YELLOW}Super-Linter has finished!{RESET} ✨\n")

    summary_file = Path("super-linter-output/super-linter-summary.md")
    if summary_file.exists():
        print(summary_file.read_text())

if __name__ == "__main__":
    main()
