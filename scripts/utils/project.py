#!/usr/bin/env python3
"""
Resolve the project root directory based on `pyproject.toml`.

Usage (Python):
    from . import get_project_root
    project_dir = get_project_root()
"""

from pathlib import Path


def get_project_root() -> Path:
    """
    Locate the project root directory based on `pyproject.toml`.

    Returns:
        Path: Absolute path to project root.

    Raises:
        RuntimeError: If no `pyproject.toml` is found in any parent directory.
    """
    current = Path(__file__).resolve()

    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent

    raise RuntimeError("Project root not found (pyproject.toml missing)")
