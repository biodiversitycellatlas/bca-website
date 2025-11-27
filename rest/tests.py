import os.path

from django.core.files import File as DjangoFile
from rest_framework import status
from rest_framework.test import APITestCase

from app.models import Species, Dataset, Gene, SingleCell, Metacell, MetacellType, DatasetFile


class SpeciesTests(APITestCase):
    """Test Species Endpoint"""

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
    """Test Datasets Endpoint"""

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


class GeneTests(APITestCase):
    """Test Genes Endpoint"""

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


class SingleCellGeneExpressionTests(APITestCase):
    """Tests SingleCellGeneExpression Endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        species1.save()
        dataset1 = Dataset.objects.create(species=species1, name="DRat", description="rat dataset")
        dataset1.save()
        self.dataset_id = dataset1.pk
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        type1.save()
        metacell1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=3, y=5)

        for i in range(1, 5):
            gene = "g" + str(i)
            Gene.objects.create(name=gene, species=species1).save()
        self.gene_id = Gene.objects.all().first().pk

        for i in range(1, 6):
            cell = "c" + str(i)
            SingleCell.objects.create(name=cell, dataset=dataset1, metacell=metacell1).save()

        test_file = os.path.join(os.path.dirname(__file__), "test_fixtures", "gene_expression_test.hdf5")
        with open(test_file, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(test_file))
            DatasetFile.objects.get_or_create(
                dataset=dataset1, type="singlecell_umifrac", defaults={"file": django_file}
            )

    def test_retrieve(self):
        url = f"/api/v1/single_cell_expression/?dataset={self.dataset_id}&gene={self.gene_id}"
        response = self.client.get(url, format="json")
        expression_values = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(expression_values), 2)
        self.assertSetEqual({s["single_cell"] for s in expression_values}, {"c3", "c5"})
        self.assertSetEqual({s["umifrac"] for s in expression_values}, {2142.857177734375, 10000.0})


class SingleCellTests(APITestCase):
    """Tests SingleCell endpoint"""

    def setUp(self):
        species1 = Species.objects.create(common_name="species1", scientific_name="species1", description="species1")
        species1.save()
        dataset1 = Dataset.objects.create(species=species1, name="dataset1", description="dataset1")
        dataset1.save()
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        type1.save()
        metacell1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=1, y=1)
        metacell1.save()
        single_cell = SingleCell.objects.create(name="singleCell", dataset=dataset1, metacell=metacell1)
        single_cell.save()

    def test_retrieve(self):
        url = "/api/v1/single_cells/?dataset=species1-dataset1"
        response = self.client.get(url, format="json")
        single_cells = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(single_cells), 1)
        self.assertListEqual([s["name"] for s in single_cells], ["singleCell"])
