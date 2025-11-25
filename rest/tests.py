from rest_framework import status
from rest_framework.test import APITestCase

from app.models import Species, Dataset, Gene


class SpeciesTests(APITestCase):
    """  Test Species Endpoint """

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        species1.save()
        species2 = Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")
        species2.save()

    def test_species(self):

        response = self.client.get("/api/v1/species/", format="json")
        species = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(species), 2)
        self.assertSetEqual({s["common_name"] for s in species}, {"rat", "mouse"})


class DatasetTests(APITestCase):
    """  Test Datasets Endpoint """

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        species1.save()
        species2 = Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")
        species2.save()
        dataset1 = Dataset.objects.create(species=species1, name="DRat", description="rat dataset")
        dataset1.save()
        dataset2 = Dataset.objects.create(species=species2, name="DMouse", description="mouse dataset")
        dataset2.save()

    def test_datasets(self):
        response = self.client.get("/api/v1/datasets/", format="json")
        datasets = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(datasets), 2)
        self.assertSetEqual({s["dataset"] for s in datasets}, {"DRat", "DMouse"})


class GenesTests(APITestCase):
    """ Test Genes Endpoint """

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        species1.save()
        gene1 = Gene.objects.create(species=species1, name="Gene1", description="description1")
        gene1.save()
        gene2 = Gene.objects.create(species=species1, name="Gene2", description="description2")
        gene2.save()

    def test_genes(self):
        response = self.client.get("/api/v1/genes/", format="json")
        genes = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(genes), 2)
        self.assertSetEqual({s["name"] for s in genes}, {"Gene1", "Gene2"})
