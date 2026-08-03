"""Test app utility functions."""

from django.test import TestCase

from app.models import Meta, Species
from app.utils import get_dataset_dict, get_species_dict


class SpeciesDictTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = cls.species.datasets.create(name="adult")
        Meta.objects.create(species=cls.species, key="species", value="Mus musculus")
        Meta.objects.create(species=cls.species, key="phylum", value="Chordata")
        Meta.objects.create(species=cls.species, key="kingdom", value="Animalia")

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
