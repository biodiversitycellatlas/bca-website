from django.test import TestCase, Client
from django.urls import reverse

from app.views import AtlasView
from app.models import Dataset, Species, Gene


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # runs once for the class
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = Dataset.objects.create(name="adult", species=cls.species)

        cls.brca1 = Gene.objects.create(name="Brca1", species=cls.species)
        cls.brca2 = Gene.objects.create(name="Brca2", species=cls.species)
        cls.client = Client()


class AtlasViewTest(BaseTestCase):
    def test_atlas_view_basic(self):
        response = self.client.get("/atlas/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("icon", response.context)
        self.assertIn("dataset_dict", response.context)
        self.assertIn("links", response.context)

    def test_get_species_icon_random(self):
        icon = AtlasView().get_species_icon()
        self.assertIsInstance(icon, str)

    def test_invalid_dataset_warning(self):
        response = self.client.get("/atlas/?dataset=invalid-dataset")
        self.assertIn("warning", response.context)
        self.assertIn("Invalid dataset", response.context["warning"]["title"])

    def test_invalid_dataset_redirect(self):
        response = self.client.get("/atlas/invalid/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("atlas"), response.url)


class AtlasInfoViewTest(BaseTestCase):
    def test_dataset(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/")
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["dataset"], self.dataset)
        self.assertEqual(context["species"].common_name, "mouse")
        self.assertIn("dataset_dict", context)
        self.assertIn("links", context)

        # Test quality control metrics
        self.assertIn("qc_metrics", context)
        for metric in context["qc_metrics"]:
            self.assertIn("title", metric)
            self.assertIn("values", metric)


class AtlasOverviewViewTest(BaseTestCase):
    def test_dataset(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/overview/")
        self.assertEqual(response.status_code, 200)


class AtlasGeneViewTest(BaseTestCase):
    def test_index(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/gene/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("gene", response.context)
        self.assertEqual(response.context["gene"], "")
        self.assertNotIn("warning", response.context)

    def test_valid_gene(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/gene/Brca1/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("gene", response.context)
        self.assertIsInstance(response.context["gene"], Gene)
        self.assertEqual(response.context["gene"].name, "Brca1")

        # No warnings expected
        self.assertNotIn("warning", response.context)

    def test_invalid_gene(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/gene/invalid-gene/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["gene"], "")
        self.assertIn("warning", response.context)

        # Raise warning for invalid gene
        warning = response.context["warning"]
        self.assertIn("Invalid gene", warning["title"])
        self.assertIn("Please check available genes", warning["description"])


class AtlasPanelViewTest(BaseTestCase):
    def test_gene_panel(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/panel/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("metacell_dict", response.context)


class AtlasMarkersViewTest(BaseTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/markers/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("metacell_dict", response.context)


class AtlasCompareViewTest(BaseTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.dataset.slug}/compare/")
        self.assertEqual(response.status_code, 200)
