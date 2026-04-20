"""Custom django-filter filter sets and utilities for the API."""

def sort_api_tags():
    """Return sorted API tags."""

    tags = [
        "Species",
        "Dataset",
        "Gene",
        "Gene module",
        "Gene ontology",
        "Metacell",
        "Single cell",
        "Cross-species",
        "Sequence alignment",
    ]
    return [{"name": tag} for tag in tags]
