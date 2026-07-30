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
    Orthogroup,
    MetacellLink,
    SAMap,
    ExpressionConservation,
    SpeciesFile,
)


class SchemaTests(APITestCase):
    """Tests for OpenAPI schema generation."""

    def test_format_parameter_description(self):
        response = self.client.get("/api/v1/schema/", format="json")
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        params = schema["paths"]["/api/v1/species/"]["get"]["parameters"]
        format_param = next(p for p in params if p["name"] == "format")
        assert format_param["description"] == "Response format."


class SpeciesTests(APITestCase):
    """Test Species Endpoint"""

    @classmethod
    def setUpTestData(cls):
        Species.objects.create(common_name="rat", scientific_name="Rat", description="rat")
        Species.objects.create(common_name="mouse", scientific_name="Mouse", description="mouse")

    def test_retrieve(self):
        response = self.client.get("/api/v1/species/", format="json")
        species = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(species) == 2
        assert {s["common_name"] for s in species} == {"rat", "mouse"}

    def test_get(self):
        response = self.client.get("/api/v1/species/Rat/", format="json")
        species = dict(response.data)
        assert response.status_code == status.HTTP_200_OK
        assert species["common_name"] == "rat"
        assert species["scientific_name"] == "Rat"
        assert species["description"] == "rat"


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
        assert response.status_code == status.HTTP_200_OK
        assert len(datasets) == 2
        assert {s["dataset"] for s in datasets} == {"DRat", "DMouse"}

    def test_get(self):
        response = self.client.get("/api/v1/datasets/mouse-dmouse/", format="json")
        dataset = dict(response.data)
        assert response.status_code == status.HTTP_200_OK
        assert dataset["slug"] == "mouse-dmouse"
        assert dataset["dataset"] == "DMouse"
        assert dataset["species"] == "Mouse"

    def test_retrieve_stats(self):
        response = self.client.get("/api/v1/stats/", format="json")
        datasets_stats = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert {s["species"] for s in datasets_stats} == {"Mouse", "Rat"}
        assert {s["dataset"] for s in datasets_stats} == {"DMouse", "DRat"}
        assert {s["genes"] for s in datasets_stats} == {0, 0}
        assert {s["cells"] for s in datasets_stats} == {0, 0}
        assert {s["metacells"] for s in datasets_stats} == {0, 0}

    def test_get_stats(self):
        response = self.client.get("/api/v1/stats/rat-drat/", format="json")
        dataset_stats = dict(response.data)
        assert response.status_code == status.HTTP_200_OK
        assert dataset_stats["dataset"] == "DRat"
        assert dataset_stats["species"] == "Rat"
        assert dataset_stats["genes"] == 0
        assert dataset_stats["cells"] == 0


class GeneTests(APITestCase):
    """Test Genes Endpoint"""

    @classmethod
    def setUpTestData(cls):
        mouse = Species.objects.create(scientific_name="Mus musculus")
        mouse.genes.create(name="Gene1")
        mouse.genes.create(name="Gene2")
        mouse.genes.create(name="Gene3")

    def test_get(self):
        url = "/api/v1/genes/"
        response = self.client.get(url, format="json")
        genes = response.data["results"]

        assert response.status_code == status.HTTP_200_OK
        assert len(genes) == 3
        assert {s["gene"] for s in genes} == {"Gene1", "Gene2", "Gene3"}

    def test_get_filtered_by_genes(self):
        subset = {"Gene1", "Gene3"}
        url = "/api/v1/genes/?genes=" + ",".join(subset)
        response = self.client.get(url, format="json")
        genes = response.data["results"]

        assert response.status_code == status.HTTP_200_OK
        assert len(genes) == 2
        assert {s["gene"] for s in genes} == subset

    def test_post(self):
        url = "/api/v1/genes/"
        payload = {}

        response = self.client.post(url, payload, format="json")
        genes = response.data["results"]

        assert response.status_code == status.HTTP_200_OK
        assert len(genes) == 0
        assert genes == []

    def test_post_filtered_by_genes(self):
        url = "/api/v1/genes/"
        payload = {"genes": {"Gene1", "Gene3"}}
        response = self.client.post(url, payload, format="json")
        genes = response.data["results"]

        assert response.status_code == status.HTTP_200_OK
        assert len(genes) == 2
        assert {s["gene"] for s in genes} == payload["genes"]


class GeneSearchTests(APITestCase):
    """Test GeneSearch Endpoint"""

    @classmethod
    def setUpTestData(cls):
        mouse = Species.objects.create(scientific_name="Mus musculus")
        cls.adult_mouse = mouse.datasets.create(name="adult")

        # Create genes
        mouse.genes.create(name="Trp53")
        mouse.genes.create(name="Actb")
        mouse.genes.create(name="Gapdh", description="Green-yellow submarine")
        mouse.genes.create(name="Myc", description="Green-yellow submarine")
        mouse.genes.create(name="Brca1")
        mouse.genes.create(name="Brca2")
        mouse.genes.create(name="Ptprc")
        mouse.genes.create(name="Il6", description="Green-yellow submarine")
        mouse.genes.create(name="Tnf")
        mouse.genes.create(name="Sox2")
        genes = mouse.genes.all()

        # Create modules
        module1 = cls.adult_mouse.gene_modules.create(name="blue")
        module2 = cls.adult_mouse.gene_modules.create(name="green")
        module3 = cls.adult_mouse.gene_modules.create(name="yellow")
        module1.genes.add(*genes[0:4])
        module2.genes.add(*genes[4:6])
        module3.genes.add(*genes[6:10])

        # Create gene lists
        genelist1 = GeneList.objects.create(name="RBP", description="RNA-binding proteins")
        genelist2 = GeneList.objects.create(name="TF", description="Transcription factors")
        genelist3 = GeneList.objects.create(name="Custom list", description="List of Brca genes")
        genelist1.genes.add(*genes[0:7])
        genelist2.genes.add(*genes[5:10])
        genelist3.genes.add(*mouse.genes.filter(name__startswith="Brca"))

        # Create domains
        domain1 = Domain.objects.create(name="Kinase")
        domain2 = Domain.objects.create(name="Zinc finger")
        domain1.gene_set.add(*genes[0:3])
        domain2.gene_set.add(*genes[4:6])

    def test_get(self):
        """Test setting dataset only."""
        dataset = self.adult_mouse.slug
        limit = 3
        url = f"/api/v1/gene_search/?dataset={dataset}&limit={limit}"
        response = self.client.get(url, format="json")
        data = response.data

        assert response.status_code == status.HTTP_200_OK
        assert {s["gene"] for s in data["genes"]} == {"Actb", "Brca1", "Brca2"}
        assert {s["name"] for s in data["gene_lists"]} == {"RBP", "TF", "Custom list"}
        assert {s["module"] for s in data["gene_modules"]} == {"blue", "green", "yellow"}
        assert {s["name"] for s in data["domains"]} == {"Kinase", "Zinc finger"}

    def test_get_query(self):
        """Test setting query string."""

        # Test gene name (also matches the description of a list)
        dataset = self.adult_mouse.slug
        limit = 3
        q = "brca"
        url = f"/api/v1/gene_search/?dataset={dataset}&limit={limit}&q={q}"
        response = self.client.get(url, format="json")
        data = response.data

        assert response.status_code == status.HTTP_200_OK
        assert {s["gene"] for s in data["genes"]} == {"Brca1", "Brca2"}
        assert {s["name"] for s in data["gene_lists"]} == {"Custom list"}
        assert data["gene_modules"] == []
        assert data["domains"] == []

        # Test module name (also matches description of a few genes)
        dataset = self.adult_mouse.slug
        limit = 3
        q = "yellow"
        url = f"/api/v1/gene_search/?dataset={dataset}&limit={limit}&q={q}"
        response = self.client.get(url, format="json")
        data = response.data

        assert response.status_code == status.HTTP_200_OK
        assert {s["gene"] for s in data["genes"]} == {"Gapdh", "Myc", "Il6"}
        assert data["gene_lists"] == []
        assert {s["module"] for s in data["gene_modules"]} == {"yellow"}
        assert data["domains"] == []


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
        assert response.status_code == status.HTTP_200_OK
        assert len(expression_values) == 2
        assert {s["single_cell"] for s in expression_values} == {"c3", "c5"}
        for entry in expression_values:
            if entry["single_cell"] == "c3":
                assert math.isclose(float(entry["umifrac"]), 2142.857, rel_tol=0.001)
            if entry["single_cell"] == "c5":
                assert math.isclose(float(entry["umifrac"]), 10000, rel_tol=0.001)


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
        assert response.status_code == status.HTTP_200_OK
        assert len(single_cells) == 1
        assert [s["name"] for s in single_cells] == ["singleCell"]


class MetacellTests(APITestCase):
    """Test Metacell endpoint"""

    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(common_name="species3", scientific_name="species3", description="species3")
        dataset1 = species1.datasets.create(name="dataset3", description="dataset3")

        type1 = dataset1.metacell_types.create(name="type1")
        meta1 = dataset1.metacells.create(name="meta1", type=type1, x=1, y=1)
        meta2 = dataset1.metacells.create(name="meta2", type=type1, x=2, y=2)
        MetacellLink.objects.create(dataset=dataset1, metacell=meta1, metacell2=meta2)

        gene1 = species1.genes.create(name="gene1", description="gene1")
        dataset1.mge.create(gene=gene1, metacell=meta1, umi_raw=1, umifrac=1.41, fold_change=4)
        dataset1.mge.create(gene=gene1, metacell=meta2, umi_raw=1, umifrac=1.41, fold_change=5)

        gene2 = species1.genes.create(name="gene2", description="gene2")
        dataset1.mge.create(gene=gene2, metacell=meta1, umi_raw=6, umifrac=2.34, fold_change=2.10)
        dataset1.mge.create(gene=gene2, metacell=meta2, umi_raw=3, umifrac=1.01, fold_change=1.85)

    def test_retrieve(self):
        url = "/api/v1/metacells/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacells = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(metacells) == 2
        assert {s["name"] for s in metacells} == {"meta1", "meta2"}

    def test_retrieve_links(self):
        url = "/api/v1/metacell_links/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacell_links = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(metacell_links) == 1
        assert metacell_links[0]["metacell"] == "meta1"
        assert metacell_links[0]["metacell2"] == "meta2"

    def test_retrieve_gene_expression(self):
        url = "/api/v1/metacell_expression/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        metacell_gene_expression = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(metacell_gene_expression) == 4
        assert {s["gene_name"] for s in metacell_gene_expression} == {"gene1", "gene2"}
        assert {s["metacell_name"] for s in metacell_gene_expression} == {"meta1", "meta2"}

    def test_retrieve_gene_expression_single_gene(self):
        url = "/api/v1/metacell_expression/?dataset=species3-dataset3&genes=gene2"
        response = self.client.get(url, format="json")
        metacell_gene_expression = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(metacell_gene_expression) == 2
        assert {s["gene_name"] for s in metacell_gene_expression} == {"gene2"}
        assert {s["metacell_name"] for s in metacell_gene_expression} == {"meta1", "meta2"}

    def test_retrieve_cell_markers(self):
        url = "/api/v1/markers/?dataset=species3-dataset3&metacells=meta1&fc_min_type=mean"
        response = self.client.get(url, format="json")
        markers = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(markers) == 2
        assert markers[0]["name"] == "gene1"


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

        assert response.status_code == status.HTTP_200_OK
        assert len(genelists) == 2
        assert {s["name"] for s in genelists} == {"geneList1", "geneList2"}


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
        assert response.status_code == status.HTTP_200_OK
        assert len(domains) == 2
        assert {s["name"] for s in domains} == {"Domain1", "Domain2"}


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
        assert response.status_code == status.HTTP_200_OK
        assert len(correlations) == 3
        assert {s["gene"] for s in correlations} == {"gene3", "gene2", "gene4"}
        assert {s["spearman"] for s in correlations} == {0.5, 0.4, 0.56}
        assert {s["pearson"] for s in correlations} == {0.8, 0.7, 0.6}


class OrthologsTests(APITestCase):
    """Tests Orthologs endpoint"""

    @classmethod
    def setUpTestData(cls):
        cls.species1 = Species.objects.create(
            common_name="species1", scientific_name="species1", description="species1"
        )
        cls.gene1 = Gene.objects.create(species=cls.species1, name="gene1", description="gene1")
        cls.gene2 = Gene.objects.create(species=cls.species1, name="gene2", description="gene2")
        cls.gene3 = Gene.objects.create(species=cls.species1, name="gene3", description="gene3")
        cls.gene4 = Gene.objects.create(species=cls.species1, name="gene4", description="gene4")

        cls.og1 = Orthogroup.objects.create(name="orthogroup1")
        cls.species1.orthologs.create(orthogroup=cls.og1, gene=cls.gene1)
        cls.species1.orthologs.create(orthogroup=cls.og1, gene=cls.gene2)
        cls.species1.orthologs.create(orthogroup=cls.og1, gene=cls.gene3)
        cls.species1.orthologs.create(orthogroup=cls.og1, gene=cls.gene4)

    def test_retrieve(self):
        url = "/api/v1/orthologs/"
        response = self.client.get(url, format="json")
        orthologs = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(orthologs) == 4
        assert {s["gene_name"] for s in orthologs} == {"gene1", "gene2", "gene3", "gene4"}

    def test_counts(self):
        url = "/api/v1/ortholog_counts/"
        response = self.client.get(url, format="json")
        ortholog_counts = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(ortholog_counts) == 1
        assert ortholog_counts[0]["species"] == "species1"
        assert ortholog_counts[0]["gene_count"] == 4


class ExpressionConservationTests(OrthologsTests):
    """Tests ExpressionConservation endpoint"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        species2 = Species.objects.create(common_name="species2", scientific_name="species2", description="species2")
        cls.dataset = cls.species1.datasets.create(name="dataset")
        cls.dataset2 = species2.datasets.create(name="dataset2")
        cls.gene5 = species2.genes.create(name="gene5", description="gene5")
        og2 = Orthogroup.objects.create(name="orthogroup2")
        ExpressionConservation.objects.create(
            orthogroup=cls.og1,
            gene=cls.gene1,
            gene2=cls.gene5,
            dataset=cls.dataset,
            dataset2=cls.dataset2,
            conservation_score=0.9,
            is_one_to_one=True,
        )
        ExpressionConservation.objects.create(
            orthogroup=cls.og1,
            gene=cls.gene2,
            gene2=cls.gene5,
            dataset=cls.dataset,
            dataset2=cls.dataset2,
            conservation_score=0.8,
            is_one_to_one=True,
        )
        ExpressionConservation.objects.create(
            orthogroup=og2,
            gene=cls.gene3,
            gene2=cls.gene5,
            dataset=cls.dataset,
            dataset2=cls.dataset2,
            conservation_score=0.5,
            is_one_to_one=False,
        )

    def test_retrieve(self):
        url = "/api/v1/expression_conservation/"
        response = self.client.get(url, format="json")
        results = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == 3
        assert {r["gene"] for r in results} == {"gene1", "gene2", "gene3"}
        assert {r["conservation_score"] for r in results} == {0.9, 0.8, 0.5}

    def test_str(self):
        ec = ExpressionConservation.objects.first()
        assert str(ec) == f"{ec.gene} - {ec.gene2} ({ec.orthogroup.name})"

    def test_filter_by_gene(self):
        url = "/api/v1/expression_conservation/?gene=gene1"
        response = self.client.get(url, format="json")
        results = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == 1
        assert results[0]["gene"] == "gene5"
        assert results[0]["conservation_score"] == 0.9

    def test_filter_by_orthogroup(self):
        url = "/api/v1/expression_conservation/?orthogroup=orthogroup1"
        response = self.client.get(url, format="json")
        results = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == 2
        url = "/api/v1/expression_conservation/?orthogroup=orthogroup2"
        response = self.client.get(url, format="json")
        results = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == 1

    def test_filter_by_is_one_to_one(self):
        url = "/api/v1/expression_conservation/?is_one_to_one=true"
        response = self.client.get(url, format="json")
        results = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == 2

    def test_filter_by_dataset(self):
        url = "/api/v1/expression_conservation/?dataset=species1-dataset"
        response = self.client.get(url, format="json")
        results = response.data["results"]
        assert response.status_code == status.HTTP_200_OK
        assert len(results) == 3


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
        assert response.status_code == status.HTTP_200_OK
        assert len(samaps) == 2
        assert {s["metacell_type"] for s in samaps} == {"type1", "type2"}
        assert {s["metacell2_type"] for s in samaps} == {"type3", "type4"}
        assert {s["samap"] for s in samaps} == {0.8, 0.7}


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
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
            SpeciesFile.objects.get_or_create(species=species1, type="DIAMOND", defaults={"file": django_file})

    def check_expected_alignment(self, response):
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["query"] == "query"
        assert response.data[0]["target"] == "P0"
        assert response.data[0]["identity"] == "100"
        assert response.data[0]["length"] == "26"
        assert response.data[0]["mismatch"] == "0"
        assert response.data[0]["gaps"] == "0"
        assert response.data[0]["query_start"] == "1"
        assert response.data[0]["query_end"] == "26"
        assert response.data[0]["target_start"] == "1"
        assert response.data[0]["target_end"] == "26"
        assert response.data[0]["e_value"] == "4.41e-17"
        assert response.data[0]["bit_score"] == "51.6"

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


class MetacellMarkerRawSQLTests(APITestCase):
    """Cover the raw-SQL ``MetacellMarkerViewSet`` (CTE-based markers query)."""

    @classmethod
    def setUpTestData(cls):
        species = Species.objects.create(common_name="cellb", scientific_name="cellb", description="cellb")
        dataset = species.datasets.create(name="atlas3", description="atlas3")

        bcell = dataset.metacell_types.create(name="B cell")
        tcell = dataset.metacell_types.create(name="T cell")

        mb1 = dataset.metacells.create(name="mb1", type=bcell, x=1, y=1)
        mb2 = dataset.metacells.create(name="mb2", type=bcell, x=2, y=2)
        mt1 = dataset.metacells.create(name="mt1", type=tcell, x=3, y=3)
        mt2 = dataset.metacells.create(name="mt2", type=tcell, x=4, y=4)

        gene_marker = species.genes.create(name="gene_marker", description="B cell marker")
        gene_low = species.genes.create(name="gene_low", description="below threshold")
        gene_t = species.genes.create(name="gene_t", description="T cell marker")

        # gene_marker: high fold-change in B cells, low in T cells
        dataset.mge.create(gene=gene_marker, metacell=mb1, umi_raw=5, umifrac=0.5, fold_change=4)
        dataset.mge.create(gene=gene_marker, metacell=mb2, umi_raw=3, umifrac=0.3, fold_change=5)
        dataset.mge.create(gene=gene_marker, metacell=mt1, umi_raw=1, umifrac=0.1, fold_change=1.0)
        dataset.mge.create(gene=gene_marker, metacell=mt2, umi_raw=2, umifrac=0.2, fold_change=1.2)

        # gene_low: never crosses fc_min=2 in B cells
        dataset.mge.create(gene=gene_low, metacell=mb1, umi_raw=1, umifrac=0.1, fold_change=0.5)
        dataset.mge.create(gene=gene_low, metacell=mb2, umi_raw=1, umifrac=0.1, fold_change=0.4)
        dataset.mge.create(gene=gene_low, metacell=mt1, umi_raw=1, umifrac=0.1, fold_change=0.6)
        dataset.mge.create(gene=gene_low, metacell=mt2, umi_raw=1, umifrac=0.1, fold_change=0.5)

        # gene_t: foreground for T cells only — must NOT appear for B cell query
        dataset.mge.create(gene=gene_t, metacell=mb1, umi_raw=1, umifrac=0.1, fold_change=1.0)
        dataset.mge.create(gene=gene_t, metacell=mb2, umi_raw=1, umifrac=0.1, fold_change=0.9)
        dataset.mge.create(gene=gene_t, metacell=mt1, umi_raw=5, umifrac=0.5, fold_change=4.0)
        dataset.mge.create(gene=gene_t, metacell=mt2, umi_raw=4, umifrac=0.4, fold_change=4.5)

    def _get_markers(self, **params):
        # ``data`` is URL-encoded by the test client, which matters for values
        # containing spaces (e.g., ``metacells="B cell"``).
        return self.client.get("/api/v1/markers/", data=params, format="json")

    def test_select_by_metacell_type_name(self):
        """Foreground selection via metacell *type* name ('B cell') uses the mct.name branch."""
        response = self._get_markers(dataset="cellb-atlas3", metacells="B cell", fc_min_type="mean", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        markers = response.data["results"]
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["name"], "gene_marker")

    def test_select_by_metacell_name(self):
        """Foreground selection via metacell name uses the mc.name branch."""
        response = self._get_markers(dataset="cellb-atlas3", metacells="mb1,mb2", fc_min_type="mean", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        markers = response.data["results"]
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["name"], "gene_marker")

    def test_annotation_values(self):
        """The raw query returns the expected sum/mean/median/percentage stats."""
        response = self._get_markers(dataset="cellb-atlas3", metacells="B cell", fc_min_type="mean", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        marker = response.data["results"][0]
        self.assertEqual(marker["name"], "gene_marker")
        # fg metacells: mb1 (umi=5), mb2 (umi=3); bg metacells: mt1 (umi=1), mt2 (umi=2)
        self.assertAlmostEqual(marker["fg_sum_umi"], 8.0, places=4)
        self.assertAlmostEqual(marker["bg_sum_umi"], 3.0, places=4)
        self.assertAlmostEqual(marker["umi_perc"], 8.0 / 11.0 * 100, places=4)
        # fg fold_changes: 4, 5 → mean 4.5, median 4.5
        self.assertAlmostEqual(marker["fg_mean_fc"], 4.5, places=4)
        self.assertAlmostEqual(marker["fg_median_fc"], 4.5, places=4)

    def test_median_threshold_filters_same_genes(self):
        """fc_min_type=median routes the HAVING to fg_median_fc."""
        response = self._get_markers(dataset="cellb-atlas3", metacells="B cell", fc_min_type="median", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        markers = response.data["results"]
        self.assertEqual({m["name"] for m in markers}, {"gene_marker"})

    def test_fc_min_excludes_all(self):
        """A high fc_min returns an empty result set."""
        response = self._get_markers(dataset="cellb-atlas3", metacells="B cell", fc_min_type="mean", fc_min=10)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_missing_dataset_returns_400(self):
        response = self.client.get("/api/v1/markers/?metacells=B cell", format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_metacells_returns_400(self):
        response = self.client.get("/api/v1/markers/?dataset=cellb-atlas3", format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_fc_min_type_returns_400(self):
        response = self._get_markers(dataset="cellb-atlas3", metacells="B cell", fc_min_type="invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_fc_min_returns_400(self):
        """A non-numeric fc_min is rejected with a 400 rather than crashing."""
        response = self._get_markers(dataset="cellb-atlas3", metacells="B cell", fc_min="notanumber")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fc_min", response.data)

    def test_unknown_dataset_returns_400(self):
        """An unresolvable dataset slug yields a 400 with a message built from the
        slug, not from the underlying exception (guards against detail leakage)."""
        response = self._get_markers(dataset="does-not-exist", metacells="B cell", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dataset", response.data)


class MetacellMarkerOrderingTests(APITestCase):
    """Regression tests for marker ordering and foreground/background partitioning.

    Guards the ``ORDER BY {having_col} DESC`` clause of ``_MARKER_SQL``: results
    must come back strongest-first, and genes that are markers only in the
    background metacells must never appear.
    """

    @classmethod
    def setUpTestData(cls):
        species = Species.objects.create(common_name="ord", scientific_name="ord", description="ord")
        dataset = species.datasets.create(name="atlas4", description="atlas4")
        cls.slug = "ord-atlas4"

        bcell = dataset.metacell_types.create(name="B cell")
        tcell = dataset.metacell_types.create(name="T cell")

        # Foreground (B cell) and background (T cell) metacells.
        fg1 = dataset.metacells.create(name="fg1", type=bcell, x=1, y=1)
        fg2 = dataset.metacells.create(name="fg2", type=bcell, x=2, y=2)
        bg1 = dataset.metacells.create(name="bg1", type=tcell, x=3, y=3)
        bg2 = dataset.metacells.create(name="bg2", type=tcell, x=4, y=4)

        # Three markers above fc_min=2 with distinct foreground fold-changes,
        # so both the mean and median HAVING columns rank them hi > mid > lo.
        for name, fg_fc in (("gene_hi", 5.0), ("gene_mid", 3.0), ("gene_lo", 2.5)):
            gene = species.genes.create(name=name, description=name)
            dataset.mge.create(gene=gene, metacell=fg1, umi_raw=4, umifrac=0.4, fold_change=fg_fc)
            dataset.mge.create(gene=gene, metacell=fg2, umi_raw=4, umifrac=0.4, fold_change=fg_fc)
            dataset.mge.create(gene=gene, metacell=bg1, umi_raw=1, umifrac=0.1, fold_change=1.0)
            dataset.mge.create(gene=gene, metacell=bg2, umi_raw=1, umifrac=0.1, fold_change=1.0)

        # Background-only marker: high in T cells, low in B cells → must be excluded.
        gene_bg = species.genes.create(name="gene_bg_only", description="background marker")
        dataset.mge.create(gene=gene_bg, metacell=fg1, umi_raw=1, umifrac=0.1, fold_change=1.0)
        dataset.mge.create(gene=gene_bg, metacell=fg2, umi_raw=1, umifrac=0.1, fold_change=0.9)
        dataset.mge.create(gene=gene_bg, metacell=bg1, umi_raw=5, umifrac=0.5, fold_change=6.0)
        dataset.mge.create(gene=gene_bg, metacell=bg2, umi_raw=5, umifrac=0.5, fold_change=6.5)

    def _get_markers(self, **params):
        return self.client.get("/api/v1/markers/", data=params, format="json")

    def test_results_ordered_by_mean_fold_change_desc(self):
        response = self._get_markers(dataset=self.slug, metacells="B cell", fc_min_type="mean", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        markers = response.data["results"]
        # Background-only gene excluded; the three foreground markers, strongest first.
        self.assertEqual([m["name"] for m in markers], ["gene_hi", "gene_mid", "gene_lo"])
        fg_means = [m["fg_mean_fc"] for m in markers]
        self.assertEqual(fg_means, sorted(fg_means, reverse=True))

    def test_results_ordered_by_median_fold_change_desc(self):
        response = self._get_markers(dataset=self.slug, metacells="B cell", fc_min_type="median", fc_min=2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        markers = response.data["results"]
        self.assertEqual([m["name"] for m in markers], ["gene_hi", "gene_mid", "gene_lo"])
        fg_medians = [m["fg_median_fc"] for m in markers]
        self.assertEqual(fg_medians, sorted(fg_medians, reverse=True))
