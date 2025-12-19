import math
import os.path

from django.core.files import File as DjangoFile
from rest_framework import status
from rest_framework.test import APITestCase

from app.models import (
    Species,
    Dataset,
    Gene,
    SingleCell,
    Metacell,
    MetacellType,
    DatasetFile,
    GeneList,
    Domain,
    GeneCorrelation,
    Ortholog,
    MetacellLink,
    MetacellGeneExpression,
    SAMap,
)


class SpeciesTests(APITestCase):
    """Test Species Endpoint"""

    @classmethod
    def setUpTestData(cls):
        Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")

    def test_retrieve(self):
        response = self.client.get("/api/v1/species/", format="json")
        species = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(species), 2)
        self.assertSetEqual({s["common_name"] for s in species}, {"rat", "mouse"})

    def test_get(self):
        response = self.client.get("/api/v1/species/Rat/", format="json")
        species = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = {
            "common_name": "rat",
            "scientific_name": "Rat",
            "html": "\n"
            '            <a class="d-flex align-items-center gap-1" href="/entry/species/Rat/">\n'
            '                <img class="rounded" alt="Image of Rat"\n'
            '                     width="25px" src="None">\n'
            "                <span><i>Rat</i></span>\n"
            "            </a>\n        ",
            "description": "rat",
            "image_url": None,
            "meta": [],
            "files": [],
            "datasets": [],
        }
        self.assertEqual(species, expected)


class DatasetTests(APITestCase):
    """Test Datasets Endpoint"""

    @classmethod
    def setUpTestData(cls):
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

    @classmethod
    def setUpTestData(cls):
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

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        dataset1 = Dataset.objects.create(species=species1, name="DRat", description="rat dataset")
        cls.dataset_id = dataset1.pk
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

    @classmethod
    def setUpTestData(cls):
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

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species3", scientific_name="species3", description="species3")
        dataset1 = Dataset.objects.create(species=species1, name="dataset3", description="dataset3")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        meta1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=1, y=1)
        meta2 = Metacell.objects.create(name="meta2", dataset=dataset1, type=type1, x=2, y=2)
        MetacellLink.objects.create(dataset=dataset1, metacell=meta1, metacell2=meta2)
        MetacellGeneExpression.objects.create(
            dataset=dataset1, gene=gene1, metacell=meta1, umi_raw=1, umifrac=1.41, fold_change=4
        )
        MetacellGeneExpression.objects.create(
            dataset=dataset1, gene=gene1, metacell=meta2, umi_raw=1, umifrac=1.41, fold_change=5
        )

    def test_retrieve(self):
        url = "/api/v1/metacells/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacells = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(metacells), 2)
        self.assertSetEqual({s["name"] for s in metacells}, {"meta1", "meta2"})

    def test_retrieve_links(self):
        url = "/api/v1/metacell_links/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacell_links = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(metacell_links), 1)
        self.assertEqual(metacell_links[0]["metacell"], "meta1")
        self.assertEqual(metacell_links[0]["metacell2"], "meta2")

    def test_retrieve_gene_expression(self):
        url = "/api/v1/metacell_expression/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacell_gene_expression = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(metacell_gene_expression), 2)
        self.assertSetEqual({s["metacell_name"] for s in metacell_gene_expression}, {"meta1", "meta2"})

    def test_retrieve_cell_markers(self):
        url = "/api/v1/markers/?dataset=species3-dataset3&metacells=meta1&fc_min_type=mean"
        response = self.client.get(url, format="json")
        markers = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["name"], "gene1")


class GeneListTests(APITestCase):
    """Tests GeneList endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species1", scientific_name="species1", description="species1")
        genelist1 = GeneList.objects.create(name="geneList1", description="geneList1")
        genelist2 = GeneList.objects.create(name="geneList2", description="geneList2")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        gene1.genelists.set([genelist1, genelist2])

    def test_retrieve(self):
        url = "/api/v1/gene_lists/?dataset=species1-dataset1"
        response = self.client.get(url, format="json")
        genelists = response.data["results"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(genelists), 2)
        self.assertSetEqual({s["name"] for s in genelists}, {"geneList1", "geneList2"})


class DomainsTest(APITestCase):
    """Tests Domains endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species1", scientific_name="species1", description="species1")
        domain1 = Domain.objects.create(name="Domain1")
        domain2 = Domain.objects.create(name="Domain2")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        gene1.domains.set([domain1, domain2])
        gene1.save()

    def test_retrieve(self):
        url = "/api/v1/domains/"
        response = self.client.get(url, format="json")
        domains = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(domains), 2)
        self.assertSetEqual({s["name"] for s in domains}, {"Domain1", "Domain2"})


class CorrelatedGenesTest(APITestCase):
    """Tests CorrelatedGenes endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species1", scientific_name="species1", description="species1")
        dataset1 = Dataset.objects.create(species=species1, name="dataset1", description="dataset1")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        gene2 = Gene.objects.create(species=species1, name="gene2", description="gene2")
        gene3 = Gene.objects.create(species=species1, name="gene3", description="gene3")
        gene4 = Gene.objects.create(species=species1, name="gene4", description="gene4")
        GeneCorrelation.objects.create(dataset=dataset1, gene=gene1, gene2=gene2, spearman=0.5, pearson=0.8)
        GeneCorrelation.objects.create(dataset=dataset1, gene=gene1, gene2=gene3, spearman=0.4, pearson=0.7)
        GeneCorrelation.objects.create(dataset=dataset1, gene=gene1, gene2=gene4, spearman=0.56, pearson=0.6)

    def test_retrieve(self):
        url = "/api/v1/correlated/?dataset=species1-dataset1&gene=gene1"
        response = self.client.get(url, format="json")
        correlations = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(correlations), 3)
        self.assertSetEqual({s["spearman"] for s in correlations}, {0.5, 0.4, 0.56})
        self.assertSetEqual({s["pearson"] for s in correlations}, {0.8, 0.7, 0.6})


class OrthologsTests(APITestCase):
    """Tests Orthologs endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species1", scientific_name="species1", description="species1")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        gene2 = Gene.objects.create(species=species1, name="gene2", description="gene2")
        gene3 = Gene.objects.create(species=species1, name="gene3", description="gene3")
        gene4 = Gene.objects.create(species=species1, name="gene4", description="gene4")
        Ortholog.objects.create(species=species1, gene=gene1, orthogroup="orthogroup1")
        Ortholog.objects.create(species=species1, gene=gene2, orthogroup="orthogroup1")
        Ortholog.objects.create(species=species1, gene=gene3, orthogroup="orthogroup1")
        Ortholog.objects.create(species=species1, gene=gene4, orthogroup="orthogroup1")

    def test_retrieve(self):
        url = "/api/v1/orthologs/"
        response = self.client.get(url, format="json")
        orthologs = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(orthologs), 4)
        self.assertSetEqual({s["gene_name"] for s in orthologs}, {"gene1", "gene2", "gene3", "gene4"})

    def test_counts(self):
        url = "/api/v1/ortholog_counts/"
        response = self.client.get(url, format="json")
        ortholog_counts = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(ortholog_counts), 1)
        self.assertEqual(ortholog_counts[0]["species"], "species1")
        self.assertEqual(ortholog_counts[0]["gene_count"], 4)


class SAMapTests(APITestCase):
    """Tests SAMap endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species3", scientific_name="species3", description="species3")
        species2 = Species.objects.create(common_name="species4", scientific_name="species4", description="species4")
        dataset1 = Dataset.objects.create(species=species1, name="dataset3", description="dataset3")
        dataset2 = Dataset.objects.create(species=species2, name="dataset4", description="dataset4")
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        type2 = MetacellType.objects.create(name="type2", dataset=dataset1)
        type3 = MetacellType.objects.create(name="type3", dataset=dataset2)
        type4 = MetacellType.objects.create(name="type4", dataset=dataset2)
        SAMap.objects.create(metacelltype=type1, metacelltype2=type3, samap=0.8)
        SAMap.objects.create(metacelltype=type2, metacelltype2=type4, samap=0.7)

    def test_retrieve(self):
        url = "/api/v1/samap/?dataset=species3-dataset3&dataset2=species4-dataset4"
        response = self.client.get(url, format="json")
        samaps = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(samaps), 2)
        self.assertSetEqual({s["metacell_type"] for s in samaps}, {"type1", "type2"})
        self.assertSetEqual({s["metacell2_type"] for s in samaps}, {"type3", "type4"})
        self.assertSetEqual({s["samap"] for s in samaps}, {0.8, 0.7})
