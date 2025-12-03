import math
import os.path

from django.core.files import File as DjangoFile
from rest_framework import status
from rest_framework.test import APITestCase

from app.models import Species, Dataset, Gene, SingleCell, Metacell, MetacellType, DatasetFile


class SpeciesTests(APITestCase):
    """Test Species Endpoint"""

    def setUp(self):
        Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")

    def test_species(self):
        response = self.client.get("/api/v1/species/", format="json")
        species = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(species), 2)
        self.assertSetEqual({s["common_name"] for s in species}, {"rat", "mouse"})


class DatasetTests(APITestCase):
    """Test Datasets Endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        species2 = Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")
        Dataset.objects.create(species=species1, name="DRat", description="rat dataset")
        Dataset.objects.create(species=species2, name="DMouse", description="mouse dataset")

    def test_datasets(self):
        response = self.client.get("/api/v1/datasets/", format="json")
        datasets = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(datasets), 2)
        self.assertSetEqual({s["dataset"] for s in datasets}, {"DRat", "DMouse"})


class GeneTests(APITestCase):
    """Test Genes Endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        Gene.objects.create(species=species1, name="Gene1", description="description1")
        Gene.objects.create(species=species1, name="Gene2", description="description2")

    def test_genes(self):
        response = self.client.get("/api/v1/genes/", format="json")
        genes = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(genes), 2)
        self.assertSetEqual({s["name"] for s in genes}, {"Gene1", "Gene2"})


class SingleCellGeneExpressionTests(APITestCase):
    """Tests SingleCellGeneExpression Endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        dataset1 = Dataset.objects.create(species=species1, name="DRat", description="rat dataset")
        self.dataset_id = dataset1.pk
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        metacell1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=3, y=5)

        for i in range(1, 5):
            gene = "g" + str(i)
            Gene.objects.create(name=gene, species=species1)

        for i in range(1, 6):
            cell = "c" + str(i)
            SingleCell.objects.create(name=cell, dataset=dataset1, metacell=metacell1)

        test_file = os.path.join(os.path.dirname(__file__), "test_fixtures", "gene_expression_test.hdf5")
        with open(test_file, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(test_file))
            DatasetFile.objects.get_or_create(
                dataset=dataset1, type="singlecell_umifrac", defaults={"file": django_file}
            )

    def test_retrieve(self):
        url = "/api/v1/single_cell_expression/?dataset=rat-drat&gene=g1"
        response = self.client.get(url, format="json")
        expression_values = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(expression_values), 2)
        self.assertSetEqual({s["single_cell"] for s in expression_values}, {"c3", "c5"})
        for entry in expression_values:
            if entry["single_cell"] == "c3":
                self.assertTrue(math.isclose(float(entry["umifrac"]), 2142.857, rel_tol=0.001))
            if entry["single_cell"] == "c5":
                self.assertTrue(math.isclose(float(entry["umifrac"]), 10000, rel_tol=0.001))


class SingleCellTests(APITestCase):
    """Tests SingleCell endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="species1", scientific_name="species1", description="species1")
        dataset1 = Dataset.objects.create(species=species1, name="dataset1", description="dataset1")
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        metacell1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=1, y=1)
        SingleCell.objects.create(name="singleCell", dataset=dataset1, metacell=metacell1)

    def test_retrieve(self):
        url = "/api/v1/single_cells/?dataset=species1-dataset1"
        response = self.client.get(url, format="json")
        single_cells = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(single_cells), 1)
        self.assertListEqual([s["name"] for s in single_cells], ["singleCell"])


class MetaCellTests(APITestCase):
    """Test Metacell endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="species3", scientific_name="species3", description="species3")
        dataset1 = Dataset.objects.create(species=species1, name="dataset3", description="dataset3")
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=1, y=1)
        Metacell.objects.create(name="meta2", dataset=dataset1, type=type1, x=2, y=2)

    def test_retrieve(self):
        url = "/api/v1/metacells/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacells = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(metacells), 2)
        self.assertSetEqual({s["name"] for s in metacells}, {"meta1", "meta2"})
