"""Misc utility functions."""

import json
from typing import Dict

import h5py
import numpy as np

from django.urls import reverse

from ..models import Dataset, Gene, GeneList, Species


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
            removed_terms = ["species", "phylum"]
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
            removed_terms = ["species", "phylum"]
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

    # Group by cell type
    types = {}
    for obj in metacells:
        types.setdefault(obj.type, []).append(obj)
    types = dict(sorted(types.items()))

    # Return metacells by cell types and all together
    metacell_dict = {"Cell types": types, "Metacells": list(metacells)}
    return metacell_dict


def convert_queryset_to_json(qs):
    """Convert Django queryset to JSON."""
    return json.dumps(list(qs))


def get_species(species):
    """Return species if found, oterhwise returns None."""
    if isinstance(species, Species):
        return species

    species = species.replace("_", " ")
    try:
        obj = Species.objects.get(scientific_name=species)
    except Species.DoesNotExist:
        obj = next((s for s in Species.objects.all() if species == s.slug), None)
    return obj


def get_dataset(dataset):
    """Return dataset if found, oterhwise returns None."""
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
    """Return gene list if found, oterhwise returns None."""
    if isinstance(gene_list, GeneList):
        return gene_list

    try:
        obj = GeneList.objects.get(name=gene_list)
    except GeneList.DoesNotExist:
        obj = None
    return obj


def read_hdf5(hdf_file: str, gene: str) -> Dict[str, float]:
    """Read the expression values for a given gene from HDF5 file

    Args:
        hdf_file: path to the HDF5 file
        gene: a gene, e.g ("Spolac_c99997_g1")
    Returns:
        A dictionary of cell names to UMI frac expression values, e.g.
        {"AACTC-1": 1.462, "ACCG-1": 1.235}

    """
    with h5py.File(hdf_file, "r") as f:
        expression_values = f.get(f"/{gene}", default=np.empty(0))[:]
        cell_names = f.get("/cell_names")[:]
        cell_positions_dict = create_positions_dictionary(cell_names)
        result = {}
        for elem in np.nditer(expression_values, flags=["zerosize_ok"]):
            position = int(elem["c"])
            result[cell_positions_dict[position]] = float(elem["e"])
        return result


def create_positions_dictionary(a_list: np.typing.ArrayLike) -> Dict[int, str]:
    """Create a dictionary from positions to elements in the array

    Args:
        a_list: numpy array of strings (cell names)
    Returns:
        dictionary e.g: { 0: "AAACG-1", 3:"CCTG-3"}
    """
    dictionary = {}
    for pos, value in enumerate(a_list):
        dictionary[pos] = str(value, encoding="ascii")
    return dictionary
