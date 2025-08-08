"""Misc utility functions."""

import json

from django.urls import reverse

from ..models import Dataset, Gene, GeneList, Species


def get_dataset_dict():
    """Prepare dictionary of datasets."""
    dataset_dict = {}
    for dataset in Dataset.objects.all():
        # get phylum
        try:
            phylum = dataset.species.meta_set.filter(key="phylum").values_list(
                "value", flat=True
            )[0]
        except (AttributeError, IndexError):
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ["species", "phylum"]
            meta = list(
                dataset.species.meta_set.exclude(key__in=removed_terms).values_list(
                    "value", flat=True
                )
            )
        except (AttributeError, IndexError):
            meta = []

        elem = {"dataset": dataset, "meta": meta}
        if phylum not in dataset_dict:
            dataset_dict[phylum] = [elem]
        else:
            dataset_dict[phylum].append(elem)

    # Sort dictionary by phyla, species and dataset order
    sorted_dict = {
        phylum: sorted(
            elems, key=lambda x: (str(x["dataset"].species), x["dataset"].order)
        )
        for phylum, elems in sorted(dataset_dict.items())
    }
    return sorted_dict


def get_species_dict():
    """Prepare dictionary of species."""
    species_dict = {}
    for species in Species.objects.all():
        # get phylum
        try:
            phylum = species.meta_set.filter(key="phylum").values_list(
                "value", flat=True
            )[0]
        except (AttributeError, IndexError):
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ["species", "phylum"]
            meta = list(
                species.meta_set.exclude(key__in=removed_terms).values_list(
                    "value", flat=True
                )
            )
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
            "name": "Gene panel",
            "icon": "solar-panel",
            "url_names": ["atlas_panel"],
            "url_view": "atlas_panel",
            "tooltip": "",
        },
        {
            "name": "Gene and orthologs",
            "icon": "bezier-curve",
            "url_names": ["atlas_gene"],
            "url_view": "atlas_gene",
            "tooltip": "Visualise gene and ortholog expression",
        },
        {
            "name": "Cell type markers",
            "icon": "list-ol",
            "url_names": ["atlas_markers"],
            "url_view": "atlas_markers",
            "tooltip": "Identify genes with specific expression patterns in selected metacells",
        },
        {
            "name": "Cross-species",
            "icon": "scale-unbalanced",
            "url_names": ["atlas_compare"],
            "url_view": "atlas_compare",
            "tooltip": "Compare genes between cell types of different species",
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
