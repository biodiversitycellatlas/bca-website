"""Test app utility functions."""

from django.test import TestCase

from app.models import Meta, Species
from app.utils import get_dataset_dict, get_species_dict


class SpeciesDictTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = cls.species.datasets.create(name="adult")
        cls.species.meta_set.create(key="species", value="Mus musculus")
        cls.species.meta_set.create(key="phylum", value="Chordata")
        cls.species.meta_set.create(key="kingdom", value="Animalia")

    def test_phylum_searchable_in_dataset_dict(self):
        dataset_dict = get_dataset_dict()
        meta = dataset_dict["Chordata"][0]["meta"]
        assert "Chordata" in meta
        assert "Animalia" in meta
        assert "Mus musculus" not in meta

    def test_phylum_searchable_in_species_dict(self):
        species_dict = get_species_dict()
        meta = species_dict["Chordata"][0]["meta"]
        assert "Chordata" in meta
        assert "Animalia" in meta
        assert "Mus musculus" not in meta
