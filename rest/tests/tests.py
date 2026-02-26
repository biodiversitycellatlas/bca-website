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


class GeneModulesData(APITestCase):
    """Data to test GeneModule-associated endpoints"""

    @classmethod
    def setUpTestData(cls):
        cls.species1 = Species.objects.create(scientific_name="species3")
        cls.dataset1 = cls.species1.datasets.create(name="dataset3")

        # Create modules with different number of genes
        cls.module1 = cls.dataset1.gene_modules.create(name="module_xyz")
        cls.module2 = cls.dataset1.gene_modules.create(name="module_abc")
        cls.module3 = cls.dataset1.gene_modules.create(name="module_123")
        cls.module4 = cls.dataset1.gene_modules.create(name="module_000")

        # Prepare transcription factor gene list
        tfs = GeneList.objects.create(name="Transcription factors")

        # Set up genes and their membership
        scores = [0.09, 0.51, 0.14, 0.53, 0.16, 0.05, 0.05, 0.78, 0.23, 0.64, 0.12, 0.95]
        for i, score in enumerate(scores, start=1):
            gene = cls.species1.genes.create(name=f"gene{i}")

            # First 3 genes go to module1, rest to module2
            if i <= 3:
                m = cls.module1
            elif i == 4:
                m = cls.module2
            else:
                m = cls.module3
            m.membership.create(gene=gene, membership_score=score)

            # Label some genes as TFs
            if i in [3, 5, 7, 8]:
                tfs.genes.add(gene)

        cls.genes = list(cls.species1.genes.all())

        # Dataset without gene modules
        species2 = Species.objects.create(scientific_name="species4")
        species2.datasets.create(name="dataset4")


class GeneModulesTests(GeneModulesData):
    """Tests GeneModules and GeneModuleMembership endpoint"""

    def test_retrieve_modules(self):
        url = "/api/v1/gene_modules/?dataset=species3-dataset3"
        response = self.client.get(url, format="json")
        modules = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(modules), 4)

        # Test modules with different number of genes
        expected = [
            # (name, gene_count, top_tf, gene_hubs)
            ("module_000", 0, set(), set()),
            ("module_123", 8, {"gene5", "gene7", "gene8"}, {"gene5", "gene8", "gene9", "gene10", "gene12"}),
            ("module_abc", 1, set(), {"gene4"}),
            ("module_xyz", 3, {"gene3"}, {"gene1", "gene2", "gene3"}),
        ]

        for m, (name, gene_count, top_tf, gene_hubs) in zip(modules, expected):
            self.assertEqual(m["module"], name)
            self.assertEqual(m["gene_count"], gene_count)
            self.assertSetEqual(set(m["top_tf"]), top_tf)
            self.assertSetEqual(set(m["gene_hubs"]), gene_hubs)

    def test_retrieve_ordered_modules(self):
        url = "/api/v1/gene_modules/?dataset=species3-dataset3&order_by_gene_count=true"
        response = self.client.get(url, format="json")
        modules = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(modules), 4)

        # Test sorted modules
        expected = [
            # (name, gene_count)
            ("module_123", 8),
            ("module_xyz", 3),
            ("module_abc", 1),
            ("module_000", 0),
        ]

        for m, (name, gene_count) in zip(modules, expected):
            self.assertEqual(m["module"], name)
            self.assertEqual(m["gene_count"], gene_count)

    def test_retrieve_empty_module(self):
        url = "/api/v1/gene_modules/?dataset=species4-dataset4"
        response = self.client.get(url, format="json")
        modules = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(modules, [])

    def test_retrieve_module_membership(self):
        limit = 3
        module = "module_123"
        dataset = "species3-dataset3"

        url = f"/api/v1/gene_modules_membership/?dataset={dataset}&module={module}&limit={limit}"
        response = self.client.get(url, format="json")
        membership = response.data["results"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(membership), 3)

        # Test module membership
        expected = [
            # (name, gene, score)
            ("module_123", "gene6", "0.050"),
            ("module_123", "gene7", "0.050"),
            ("module_123", "gene5", "0.160"),
        ]

        for m, (name, gene, score) in zip(membership, expected):
            self.assertEqual(m["dataset"], dataset)
            self.assertEqual(m["module"], name)
            self.assertEqual(m["gene"], gene)
            self.assertEqual(m["score"], score)


class GeneModuleSimilarity(GeneModulesData):
    """Tests GeneModuleSimilarity endpoint"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Add two genes from module3 to module2
        genes = list(cls.module3.genes.all())
        cls.module2.membership.create(gene=genes[0], membership_score=0.5)
        cls.module2.membership.create(gene=genes[1], membership_score=0.1)

    def test_retrieve_module_similarity(self):
        dataset = "species3-dataset3"

        url = f"/api/v1/gene_modules_similarity/?dataset={dataset}"
        response = self.client.get(url, format="json")
        sim = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(sim), 6)

        # Test module eigengenes
        expected = [
            # (module, module2, unique_genes_module, unique_genes_module2, intersecting)
            ("module_000", "module_123", 0, 8, 0),
            ("module_000", "module_abc", 0, 3, 0),
            ("module_000", "module_xyz", 0, 3, 0),
            ("module_123", "module_abc", 6, 1, 2),
            ("module_123", "module_xyz", 8, 3, 0),
            ("module_abc", "module_xyz", 3, 3, 0),
        ]

        for m, (module, module2, uniq, uniq2, intersecting) in zip(sim, expected):
            # Calculate Jaccard similarity index in percentage
            jaccard = round(intersecting / (uniq + uniq2 + intersecting) * 100)

            self.assertEqual(m["module"], module)
            self.assertEqual(m["module2"], module2)
            self.assertEqual(m["similarity"], jaccard)
            self.assertEqual(m["unique_genes_module"], uniq)
            self.assertEqual(m["unique_genes_module2"], uniq2)
            self.assertEqual(m["intersecting_genes"], intersecting)

    def test_retrieve_filtered_module_similarity(self):
        dataset = "species3-dataset3"
        modules = "module_123,module_abc"

        url = f"/api/v1/gene_modules_similarity/?dataset={dataset}&modules={modules}"
        response = self.client.get(url, format="json")
        sim = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(sim), 1)

        # Test module eigengenes
        expected = [
            # (module, module2, jaccard, unique_genes_module, unique_genes_module2, intersecting)
            ("module_123", "module_abc", 22, 6, 1, 2),
        ]

        for m, (module, module2, jaccard, uniq, uniq2, intersecting) in zip(sim, expected):
            self.assertEqual(m["module"], module)
            self.assertEqual(m["module2"], module2)
            self.assertEqual(m["similarity"], jaccard)
            self.assertEqual(m["unique_genes_module"], uniq)
            self.assertEqual(m["unique_genes_module2"], uniq2)
            self.assertEqual(m["intersecting_genes"], intersecting)

    def test_retrieve_filtered_module_similarity_genes(self):
        dataset = "species3-dataset3"
        modules = "module_123,module_abc"
        list_genes = 1

        url = f"/api/v1/gene_modules_similarity/?dataset={dataset}&modules={modules}&list_genes={list_genes}"
        response = self.client.get(url, format="json")
        sim = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(sim), 1)

        # Test module eigengenes
        expected = [
            # (module, module2, jaccard, unique_genes_module, unique_genes_module2, intersecting)
            ("module_123", "module_abc", 22, 6, 1, 2),
        ]

        genes_123 = ["gene5", "gene6", "gene7", "gene8", "gene9", "gene12"]
        genes_abc = ["gene4"]
        genes_both = ["gene10", "gene11"]

        for m, (module, module2, jaccard, uniq, uniq2, intersecting) in zip(sim, expected):
            self.assertEqual(m["module"], module)
            self.assertEqual(m["module2"], module2)
            self.assertEqual(m["similarity"], jaccard)
            self.assertEqual(m["unique_genes_module"], len(genes_123))
            self.assertEqual(m["unique_genes_module2"], len(genes_abc))
            self.assertEqual(m["intersecting_genes"], len(genes_both))
            self.assertEqual(m["unique_genes_module_list"], genes_123)
            self.assertEqual(m["unique_genes_module2_list"], genes_abc)
            self.assertEqual(m["intersecting_genes_list"], genes_both)


class GeneModuleEigengene(GeneModulesData):
    """Tests GeneModuleEigengene endpoint"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        m1 = cls.dataset1.metacells.create(name="1", x=0.2, y=0.5)
        m2 = cls.dataset1.metacells.create(name="2", x=0.6, y=0.2)
        m3 = cls.dataset1.metacells.create(name="3", x=0.1, y=0.8)

        cls.module1.eigengene_values.create(metacell=m1, eigengene_value=0.167)
        cls.module1.eigengene_values.create(metacell=m2, eigengene_value=0.135)
        cls.module1.eigengene_values.create(metacell=m3, eigengene_value=0.153)

        cls.module2.eigengene_values.create(metacell=m1, eigengene_value=0.696)
        cls.module2.eigengene_values.create(metacell=m2, eigengene_value=0.897)
        cls.module2.eigengene_values.create(metacell=m3, eigengene_value=0.336)

    def test_retrieve_module_eigengenes(self):
        dataset = "species3-dataset3"

        url = f"/api/v1/gene_modules_eigengenes/?dataset={dataset}"
        response = self.client.get(url, format="json")
        eigengenes = response.data["results"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(eigengenes), 6)

        # Test module eigengenes
        expected = [
            # (name, metacell, eigengene_values)
            ("module_xyz", "1", "0.167"),
            ("module_xyz", "2", "0.135"),
            ("module_xyz", "3", "0.153"),
            ("module_abc", "1", "0.696"),
            ("module_abc", "2", "0.897"),
            ("module_abc", "3", "0.336"),
        ]

        for m, (module, metacell, value) in zip(eigengenes, expected):
            self.assertEqual(m["dataset"], dataset)
            self.assertEqual(m["module"], module)
            self.assertEqual(m["metacell_name"], metacell)
            self.assertEqual(m["eigengene_value"], value)

    def test_retrieve_single_module_eigengene(self):
        module = "module_xyz"
        dataset = "species3-dataset3"

        url = f"/api/v1/gene_modules_eigengenes/?dataset={dataset}&module={module}"
        response = self.client.get(url, format="json")
        eigengene_values = response.data["results"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(eigengene_values), 3)

        # Test module eigengenes
        expected = [
            # (name, metacell, value)
            (module, "1", "0.167"),
            (module, "2", "0.135"),
            (module, "3", "0.153"),
        ]

        for m, (module, metacell, value) in zip(eigengene_values, expected):
            self.assertEqual(m["dataset"], dataset)
            self.assertEqual(m["module"], module)
            self.assertEqual(m["metacell_name"], metacell)
            self.assertEqual(m["eigengene_value"], value)

    def test_retrieve_sorted_module_eigengenes(self):
        module = "module_xyz"
        dataset = "species3-dataset3"
        sort_modules = "true"

        url = f"/api/v1/gene_modules_eigengenes/?dataset={dataset}&sort_modules={sort_modules}"
        response = self.client.get(url, format="json")
        eigengenes = response.data["results"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(eigengenes), 6)

        # Test module eigengenes
        expected = [
            # (name, metacell, value)
            ("module_abc", "1", "0.696"),
            ("module_abc", "2", "0.897"),
            ("module_abc", "3", "0.336"),
            ("module_xyz", "1", "0.167"),
            ("module_xyz", "2", "0.135"),
            ("module_xyz", "3", "0.153"),
        ]

        for m, (module, metacell, value) in zip(eigengenes, expected):
            self.assertEqual(m["dataset"], dataset)
            self.assertEqual(m["module"], module)
            self.assertEqual(m["metacell_name"], metacell)
            self.assertEqual(m["eigengene_value"], value)


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
