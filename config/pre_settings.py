"""
Functions to prepare settings.py setup.
"""

import os
import subprocess


# Global variables
def get_command_output(cmd):
    """
    Execute a shell command and return its standard output as a string.

    Args:
        cmd (str): The shell command to execute.

    Returns:
        str: The stripped standard output of the command.
    """
    run = subprocess.run(cmd, shell=True, text=True, capture_output=True, check=False)
    return run.stdout.strip()


def get_diamond_version():
    """Get version of DIAMOND installed."""
    cmd = "diamond --version | grep -Eo '[0-9.]+'"
    return get_command_output(cmd)


def get_latest_git_tag():
    """Get latest GitHub tag of this project."""
    cmd = (
        "git config --global --add safe.directory /usr/src/app && "
        "git describe --tags --abbrev=0"
    )
    return get_command_output(cmd)


# Parse environmental variables
def get_env(key, default=None, **kwargs):
    """
    Get an environment variable and optionally cast it to a specific type.

    Args:
        key (str): Name of the environment variable.
        default: Value to return if the variable is not set.
        **kwargs:
            required (bool): If True, raise RuntimeError for missing variable.
            type (str): Cast variable to 'bool', 'int', 'float', or 'array'.
            delim (str): Delimiter for 'array' type (default: ',').

    Returns:
        Value of environment variable.
    """
    env = os.getenv(key, default)
    res = env

    # Raise error if variable is required and is not defined
    required = kwargs["required"] if "required" in kwargs else False
    if required and res is None:
        raise RuntimeError(
            f"{key}: environmental variable must be defined in a .env* file"
        )

    # Parse according to variable type
    var_type = kwargs["type"] if "type" in kwargs else None

    if var_type == "bool":
        res = env == "True"
    elif var_type == "int":
        res = int(env)
    elif var_type == "float":
        res = float(env)
    elif var_type == "array":
        # Split array by comma (default)
        delim = kwargs["delim"] if "delim" in kwargs else ","
        res = env.split(delim)
    return res
