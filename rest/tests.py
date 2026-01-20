import math
import tempfile
import os.path

from django.core.files import File as DjangoFile
from django.test import override_settings
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
    SpeciesFile,
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
        species = dict(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(species["common_name"], "rat")
        self.assertEqual(species["scientific_name"], "Rat")
        self.assertEqual(species["description"], "rat")


class DatasetTests(APITestCase):
    """Test Datasets Endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        species2 = Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")
        Dataset.objects.create(species=species1, name="DRat", description="rat dataset")
        Dataset.objects.create(species=species2, name="DMouse", description="mouse dataset")

    def test_retrieve(self):
        response = self.client.get("/api/v1/datasets/", format="json")
        datasets = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(datasets), 2)
        self.assertSetEqual({s["dataset"] for s in datasets}, {"DRat", "DMouse"})

    def test_get(self):
        response = self.client.get("/api/v1/datasets/mouse-dmouse/", format="json")
        dataset = dict(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(dataset["slug"], "mouse-dmouse")
        self.assertEqual(dataset["dataset"], "DMouse")
        self.assertEqual(dataset["species"], "Mouse")

    def test_retrieve_stats(self):
        response = self.client.get("/api/v1/stats/", format="json")
        datasets_stats = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual({s["species"] for s in datasets_stats}, {"Mouse", "Rat"})
        self.assertSetEqual({s["dataset"] for s in datasets_stats}, {"DMouse", "DRat"})
        self.assertSetEqual({s["genes"] for s in datasets_stats}, {0, 0})
        self.assertSetEqual({s["cells"] for s in datasets_stats}, {0, 0})
        self.assertSetEqual({s["metacells"] for s in datasets_stats}, {0, 0})

    def test_get_stats(self):
        response = self.client.get("/api/v1/stats/rat-drat/", format="json")
        dataset_stats = dict(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(dataset_stats["dataset"], "DRat")
        self.assertEqual(dataset_stats["species"], "Rat")
        self.assertEqual(dataset_stats["genes"], 0)
        self.assertEqual(dataset_stats["cells"], 0)


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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
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


class AlignTests(APITestCase):
    """Tests Alignment endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(
            common_name="aligner", scientific_name="Alignspecies", description="Align Species"
        )
        test_file = os.path.join(os.path.dirname(__file__), "test_fixtures", "test-dmd-db.dmnd")
        with open(test_file, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(test_file))
            SpeciesFile.objects.get_or_create(
                species=species1,
                type="DIAMOND",
                defaults={"file": django_file})

    def check_expected_alignment(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["query"], "query")
        self.assertEqual(response.data[0]["target"], "P0")
        self.assertEqual(response.data[0]["identity"], "100")
        self.assertEqual(response.data[0]["length"], "26")
        self.assertEqual(response.data[0]["mismatch"], "0")
        self.assertEqual(response.data[0]["gaps"], "0")
        self.assertEqual(response.data[0]["query_start"], "1")
        self.assertEqual(response.data[0]["query_end"], "26")
        self.assertEqual(response.data[0]["target_start"], "1")
        self.assertEqual(response.data[0]["target_end"], "26")
        self.assertEqual(response.data[0]["e_value"], "4.41e-17")
        self.assertEqual(response.data[0]["bit_score"], "51.6")

    def test_get(self):
        url = "/api/v1/align/"
        path = "?sequences=MSIWFSIAILSVLVPFVQLTPIRPRS&type=aminoacids&species=Alignspecies"

        response = self.client.get(f"{url}{path}")

        self.check_expected_alignment(response)

    def test_post(self):
        url = "/api/v1/align/"
        data = dict(sequences="MSIWFSIAILSVLVPFVQLTPIRPRS", type="aminoacids", species="Alignspecies")

        response = self.client.post(url, data, format="json")

        self.check_expected_alignment(response)
