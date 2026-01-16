"""Test Cell Atlas views."""

from django.urls import reverse

from app.views import AtlasView
from app.models import Gene
from app.tests.views.utils import DataTestCase


class AtlasViewTest(DataTestCase):
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


class AtlasInfoViewTest(DataTestCase):
    def test_dataset(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/")
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["dataset"], self.adult_mouse)
        self.assertEqual(context["species"].common_name, "mouse")
        self.assertIn("dataset_dict", context)
        self.assertIn("links", context)

        # Test quality control metrics
        self.assertIn("qc_metrics", context)
        for metric in context["qc_metrics"]:
            self.assertIn("title", metric)
            self.assertIn("values", metric)


class AtlasOverviewViewTest(DataTestCase):
    def test_dataset(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/overview/")
        self.assertEqual(response.status_code, 200)


class AtlasGeneViewTest(DataTestCase):
    def test_index(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("gene", response.context)
        self.assertEqual(response.context["gene"], "")
        self.assertNotIn("warning", response.context)

    def test_valid_gene(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/{self.brca1.name}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("gene", response.context)
        self.assertIsInstance(response.context["gene"], Gene)
        self.assertEqual(response.context["gene"].name, self.brca1.name)

        # No warnings expected
        self.assertNotIn("warning", response.context)

    def test_invalid_gene(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/invalid-gene/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["gene"], "")
        self.assertIn("warning", response.context)

        # Raise warning for invalid gene
        warning = response.context["warning"]
        self.assertIn("Invalid gene", warning["title"])
        self.assertIn("Please check available genes", warning["description"])


class AtlasPanelViewTest(DataTestCase):
    def test_gene_panel(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/panel/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("metacell_dict", response.context)


class AtlasMarkersViewTest(DataTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/markers/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("metacell_dict", response.context)


class AtlasCompareViewTest(DataTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/compare/")
        self.assertEqual(response.status_code, 200)
