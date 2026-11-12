"""
Utilities for parsing Newick-format phylogenetic trees.
"""

import re


def parse_newick_labels(newick: str) -> set[str]:
    """
    Extract all node labels from a Newick string.

    Labels are the tokens between the structural characters ( ) " : ; and ,;
    [ ... ] comments and branch lengths are ignored. Quoted labels containing
    structural characters (e.g. commas) are not supported.

    Args:
        newick: Newick-formatted tree string.

    Returns:
        Set of node labels (empty labels are omitted).

    Raises:
        ValueError: If the Newick string is malformed.
    """
    s = re.sub(r"\[[^\]]*\]", "", newick)  # drop [ ... ] comments
    if s.count("(") != s.count(")") or not s.strip().endswith(";"):
        raise ValueError("Malformed Newick string.")
    s = re.sub(r":[^()\":;,]*", "", s)  # drop branch lengths
    return {label for label in re.split(r"[()\":;,]+", s) if label}
