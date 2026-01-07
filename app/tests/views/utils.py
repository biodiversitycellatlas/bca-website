"""Utilities for tests."""

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile

from app.models import Dataset, Species, Gene, SpeciesFile


class DataTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Runs once for the whole class
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = Dataset.objects.create(name="adult", species=cls.species)
        Dataset.objects.create(name="baby", species=cls.species)

        cls.brca1 = Gene.objects.create(name="Brca1", species=cls.species)
        cls.brca2 = Gene.objects.create(name="Brca2", species=cls.species)

        fasta_demo = (">Brca1\nMACDEFGHIK\nLMNPQRSTVW\n>Brca2\nMACDEFGHIK\n").encode("utf-8")

        cls.species_file = SpeciesFile.objects.create(
            species=cls.species, type="Proteome", file=SimpleUploadedFile("demo.fasta", fasta_demo)
        )

        # Prepare client
        cls.client = Client()
