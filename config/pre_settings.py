"""
Functions to properly setup settings.py.
"""

import os
import subprocess


# Global variables
def get_command_output(cmd):
    run = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return run.stdout.strip()


def get_DIAMOND_version():
    cmd = "diamond --version | grep -Eo '[0-9.]+'"
    return get_command_output(cmd)


def get_latest_git_tag():
    """Get latest GitHub tag of this project."""
    cmd = "git describe --tags --abbrev=0"
    return get_command_output(cmd)


# Parse environmental variables
def get_env(key, default=None, **kwargs):
    env = os.getenv(key, default)
    res = env

    # Raise error if variable is required and is not defined
    required = kwargs["required"] if "required" in kwargs else False
    if required and res is None:
        raise RuntimeError(
            f"{key}: environmental variable must be defined in a .env* file"
        )

    # Parse according to variable type
    type = kwargs["type"] if "type" in kwargs else None

    if type == "bool":
        res = env == "True"
    elif type == "int":
        res = int(env)
    elif type == "float":
        res = float(env)
    elif type == "array":
        # Split array by comma (default)
        delim = kwargs["delim"] if "delim" in kwargs else ","
        res = env.split(delim)
    return res
