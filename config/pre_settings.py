"""
Functions to properly setup settings.py.
"""

import subprocess

# Global variables
def get_DIAMOND_version():
    cmd = "diamond --version | grep -Eo '[0-9.]+'"
    version = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return version.stdout.strip()
