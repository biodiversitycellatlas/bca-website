from .models import Species, Dataset
import json

def getDatasetDict():
    ''' Prepare dictionary of datasets. '''
    dataset_dict = {}
    for dataset in Dataset.objects.all():
        # get phylum
        try:
            phylum = dataset.species.meta_set.filter(key="phylum").values_list('value', flat=True)[0]
        except:
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ['species', 'phylum']
            meta = list(dataset.species.meta_set.exclude(key__in=removed_terms)
                                                .values_list('value', flat=True))
        except:
            meta = list()

        elem = {'dataset': dataset, 'meta': meta}
        if phylum not in dataset_dict:
            dataset_dict[phylum] = [elem]
        else:
            dataset_dict[phylum].append(elem)

    # Sort dictionary by phyla, species and dataset order
    sorted_dict = {
        phylum: sorted(elems, key=lambda x: (
            str(x['dataset'].species), x['dataset'].order))
        for phylum, elems in sorted(dataset_dict.items())
    }
    return sorted_dict


def getSpeciesDict():
    ''' Prepare dictionary of species. '''
    species_dict = {}
    for species in Species.objects.all():
        # get phylum
        try:
            phylum = species.meta_set.filter(key="phylum").values_list('value', flat=True)[0]
        except:
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ['species', 'phylum']
            meta = list(species.meta_set.exclude(key__in=removed_terms)
                                        .values_list('value', flat=True))
        except:
            meta = list()

        elem = {'species': species, 'meta': meta}
        if phylum not in species_dict:
            species_dict[phylum] = [elem]
        else:
            species_dict[phylum].append(elem)
    return species_dict


def getMetacellDict(dataset):
    ''' Prepare dictionary of metacells for a dataset. '''
    metacells = dataset.metacells.select_related('type')

    # Group by cell type
    types = dict()
    for obj in metacells:
        types.setdefault(obj.type, []).append(obj)

    # Return metacells by cell types and all together
    metacell_dict = {'Cell types': types, 'Metacells': list(metacells)}
    return metacell_dict


def convertQuerysetToJSON(qs):
    ''' Convert Django queryset to JSON. '''
    return json.dumps(list(qs))


def getSpecies(species):
    ''' Returns species if it exists in the database; returns None otherwise. '''
    if isinstance(species, Species):
        return obj

    species = species.replace("_", " ")
    try:
        obj = Species.objects.filter(scientific_name=species)[0]
    except:
        obj = None
    return obj


def getDataset(dataset):
    ''' Returns dataset if it exists in the database; returns None otherwise. '''
    if isinstance(dataset, Dataset):
        return obj

    try:
        obj = [d for d in Dataset.objects.all() if dataset == d.slug][0]
    except:
        obj = None
    return obj
