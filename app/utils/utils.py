"""Misc utility functions."""

import json
import re
from typing import Dict

import h5py
import numpy as np

from django.urls import reverse

from ..models import Dataset, Gene, GeneList, MetacellTypeSimilarity, Ortholog, Species


def get_metacell_index(name):
    """Extract the trailing integer of a metacell name, used to order metacells.

    Args:
        name: metacell name (e.g. "acrmil01_MC_00204" or "12").

    Returns:
        Trailing integer, or None if the name has none.
    """
    match = re.search(r"(\d+)$", str(name))
    return int(match.group(1)) if match else None


def get_metacell_order(order, name):
    """Return the stored metacell order for heatmaps, falling back to the trailing
    integer of the metacell name when no order is stored.

    Args:
        order: stored metacell order (nullable).
        name: metacell name (e.g. "acrmil01_MC_00204" or "12").

    Returns:
        Metacell order, or None if none is available.
    """
    return order if order is not None else get_metacell_index(name)


def get_dataset_dict():
    """Prepare dictionary of datasets."""
    dataset_dict = {}
    for dataset in Dataset.objects.all():
        # get phylum
        try:
            phylum = dataset.species.meta_set.filter(key="phylum").values_list("value", flat=True)[0]
        except (AttributeError, IndexError):
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ["species"]
            meta = list(dataset.species.meta_set.exclude(key__in=removed_terms).values_list("value", flat=True))
        except (AttributeError, IndexError):
            meta = []

        elem = {"dataset": dataset, "meta": meta}
        if phylum not in dataset_dict:
            dataset_dict[phylum] = [elem]
        else:
            dataset_dict[phylum].append(elem)

    # Sort dictionary by phyla, species and dataset order
    sorted_dict = {
        phylum: sorted(elems, key=lambda x: (str(x["dataset"].species), x["dataset"].order))
        for phylum, elems in sorted(dataset_dict.items())
    }
    return sorted_dict


def get_compare_dataset_dict(dataset):
    """Prepare dictionary of datasets with data to compare against a given dataset.

    Only datasets from other species with cell-type similarity scores (SAMap,
    Pesci, AUCell) or shared gene module orthogroups are included.

    Args:
        dataset: Dataset to compare against.

    Returns:
        Dictionary of datasets grouped by phylum, filtered by data availability.
    """
    if not isinstance(dataset, Dataset):
        return {}

    # Datasets with cell-type similarity scores against the given dataset (either direction)
    similarity_dataset_ids = set()
    for score_field in ["samap_score", "pesci_score", "aucell_1to2"]:
        similarity_dataset_ids |= set(
            MetacellTypeSimilarity.objects.filter(
                metacelltype__dataset=dataset, **{f"{score_field}__isnull": False}
            ).values_list("metacelltype2__dataset_id", flat=True)
        ) | set(
            MetacellTypeSimilarity.objects.filter(
                metacelltype2__dataset=dataset, **{f"{score_field}__isnull": False}
            ).values_list("metacelltype__dataset_id", flat=True)
        )

    # Orthogroups containing genes from the given dataset's gene modules
    shared_orthogroups = Ortholog.objects.filter(
        gene__modules__module__dataset=dataset
    ).values_list("orthogroup_id", flat=True)

    # Datasets whose gene modules share an orthogroup with the given dataset
    module_dataset_ids = set(
        Ortholog.objects.filter(orthogroup_id__in=shared_orthogroups)
        .exclude(gene__modules__module__dataset=dataset)
        .values_list("gene__modules__module__dataset_id", flat=True)
        .distinct()
    )

    # Only datasets from other species with either type of comparison data
    eligible_ids = set(
        Dataset.objects.filter(id__in=similarity_dataset_ids | module_dataset_ids)
        .exclude(species=dataset.species)
        .values_list("id", flat=True)
    )

    dataset_dict = get_dataset_dict()
    return {
        phylum: [elem for elem in elems if elem["dataset"].id in eligible_ids]
        for phylum, elems in dataset_dict.items()
        if any(elem["dataset"].id in eligible_ids for elem in elems)
    }


def get_species_dict():
    """Prepare dictionary of species."""
    species_dict = {}
    for species in Species.objects.all():
        # get phylum
        try:
            phylum = species.meta_set.filter(key="phylum").values_list("value", flat=True)[0]
        except (AttributeError, IndexError):
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ["species"]
            meta = list(species.meta_set.exclude(key__in=removed_terms).values_list("value", flat=True))
        except (AttributeError, IndexError):
            meta = []

        elem = {"species": species, "meta": meta}
        if phylum not in species_dict:
            species_dict[phylum] = [elem]
        else:
            species_dict[phylum].append(elem)
    return species_dict


def get_metacell_dict(dataset):
    """Prepare dictionary of metacells for a dataset."""
    metacells = dataset.metacells.select_related("type")

    # Group by cell type; metacells without a type are grouped as "Unannotated"
    types = {}
    for obj in metacells:
        obj_type = obj.type or "Unannotated"
        types.setdefault(obj_type, []).append(obj)
    types = dict(sorted(types.items(), key=lambda kv: str(kv[0])))

    # Return metacells by cell types and all together
    metacell_dict = {"Cell types": types, "Metacells": list(metacells)}
    return metacell_dict


def convert_queryset_to_json(qs):
    """Convert Django queryset to JSON."""
    return json.dumps(list(qs))


def get_species(species):
    """Returns species if found, oterhwise returns None."""
    if isinstance(species, Species):
        return species

    species = species.replace("_", " ")
    try:
        obj = Species.objects.get(scientific_name=species)
    except Species.DoesNotExist:
        obj = next((s for s in Species.objects.all() if species == s.slug), None)
    return obj


def get_dataset(dataset):
    """Returns dataset if found, oterhwise returns None."""
    if isinstance(dataset, Dataset):
        return dataset

    obj = next((d for d in Dataset.objects.all() if dataset == d.slug), None)
    return obj


def parse_gene_slug(slug):
    """Parse gene slug into Gene object."""
    species, gene = slug.split("_", 1)
    species = get_species(species)
    if species is None:
        return None

    try:
        obj = Gene.objects.get(name=gene, species__scientific_name=species)
    except Gene.DoesNotExist:
        obj = None
    return obj


def get_gene_list(gene_list):
    """Returns gene list if found, oterhwise returns None."""
    if isinstance(gene_list, GeneList):
        return gene_list

    try:
        obj = GeneList.objects.get(name=gene_list)
    except GeneList.DoesNotExist:
        obj = None
    return obj


def get_cell_atlas_links(url_name, dataset=None):
    """Returns links to Cell Atlas navigation bar."""
    links = [
        {
            "name": "Information",
            "icon": "dna",
            "url_names": ["atlas", "atlas_info"],
            "url_view": "atlas_info",
            "tooltip": "",
        },
        {
            "name": "Atlas overview",
            "icon": "diagram-project",
            "url_names": ["atlas_overview"],
            "url_view": "atlas_overview",
            "tooltip": "",
        },
        {
            "name": "Gene lists",
            "icon": "solar-panel",
            "url_names": ["atlas_panel"],
            "url_view": "atlas_panel",
            "tooltip": "",
        },
        {
            "name": "Gene modules",
            "icon": "puzzle-piece",
            "url_names": ["atlas_modules"],
            "url_view": "atlas_modules",
            "tooltip": "",
        },
        {
            "name": "Cell type markers",
            "icon": "list-ol",
            "url_names": ["atlas_markers"],
            "url_view": "atlas_markers",
            "tooltip": "Identify genes with specific expression patterns in selected metacells",
        },
        {
            "name": "Gene view",
            "icon": "bezier-curve",
            "url_names": ["atlas_gene"],
            "url_view": "atlas_gene",
            "tooltip": "Visualise gene and ortholog expression",
        },
        {
            "name": "Gene ontology",
            "icon": "arrow-trend-up",
            "url_names": ["atlas_enrichment"],
            "url_view": "atlas_enrichment",
            "tooltip": "Analyze GO enrichment",
        },
        {
            "name": "Cross-species",
            "icon": "scale-unbalanced",
            "url_names": ["atlas_compare"],
            "url_view": "atlas_compare",
            "tooltip": "Compare cell types and gene modules across different species",
        },
    ]

    for link in links:
        link["active"] = url_name in link["url_names"]
        link["disabled"] = dataset is None
        if link["active"]:
            link["href"] = "#top"
        elif dataset is not None:
            link["href"] = reverse(link["url_view"], args=[dataset.slug])
        else:
            link["href"] = "#"
    return links


def read_hdf5(hdf_file: str, gene: str) -> Dict[str, float]:
    """Reads the expression values for a given gene from HDF5 file

    Args:
        hdf_file: path to the HDF5 file
        gene: a gene, e.g ("Spolac_c99997_g1")
    Returns:
        A dictionary of cell names to UMI frac expression values, e.g.
        {"AACTC-1": 1.462, "ACCG-1": 1.235}

    """
    with h5py.File(hdf_file, "r") as f:
        expression_values = f.get(f"/umifrac/{gene}", default=np.empty(0))[:]
        cell_names = f.get("/cell_names")[:]
        cell_positions_dict = create_positions_dictionary(cell_names)
        result = {}
        for elem in np.nditer(expression_values, flags=["zerosize_ok"]):
            position = int(elem["c"])
            result[cell_positions_dict[position]] = float(elem["e"])
        return result


def create_positions_dictionary(a_list: np.typing.ArrayLike) -> Dict[int, str]:
    """Creates a dictionary from positions to elements in the array

    Args:
        a_list: numpy array of strings (cell names)
    Returns:
        dictionary e.g: { 0: "AAACG-1", 3:"CCTG-3"}
    """
    dictionary = {}
    for pos, value in enumerate(a_list):
        dictionary[pos] = str(value, encoding="ascii")
    return dictionary
