"""
Functions to properly setup settings.py.
"""

import os, subprocess

# Global variables
def get_DIAMOND_version():
    cmd = "diamond --version | grep -Eo '[0-9.]+'"
    version = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return version.stdout.strip()

# Parse environmental variables
def get_env(key, default=None, **kwargs):
    env = os.getenv(key, default)
    res = env

    type = kwargs['type'] if 'type' in kwargs else None

    if type == 'bool':
        res = env == 'True'
    elif type == 'int':
        res = int(env)
    elif type == 'float':
        res = float(env)
    elif type == 'array':
        # Split array by comma (default)
        delim = kwargs['delim'] if 'delim' in kwargs else ','
        res = env.split(delim)
    return res
