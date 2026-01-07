from django.test import TestCase, RequestFactory
from django.urls import reverse
from types import SimpleNamespace

from app.views import AtlasView, BaseAtlasView, AtlasInfoView
from app.models import Dataset, Species


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # runs once for the class
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = Dataset.objects.create(name="adult", species=cls.species)

    def setUp(self):
        self.factory = RequestFactory()

    def get_atlas_request(self, url="/atlas/"):
        request = self.factory.get(url)
        request.resolver_match = SimpleNamespace(url_name="atlas")
        return request


class AtlasViewTest(BaseTestCase):
    def test_atlas_view_basic(self):
        request = self.get_atlas_request()
        response = AtlasView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("icon", response.context_data)
        self.assertIn("dataset_dict", response.context_data)
        self.assertIn("links", response.context_data)

    def test_get_species_icon_random(self):
        icon = AtlasView().get_species_icon()
        self.assertIsInstance(icon, str)

    def test_invalid_dataset_warning(self):
        request = self.get_atlas_request("/atlas/?dataset=invalid-dataset")
        response = AtlasView.as_view()(request)

        self.assertIn("warning", response.context_data)
        self.assertIn("Invalid dataset", response.context_data["warning"]["title"])


class BaseAtlasViewTest(BaseTestCase):
    def test_valid_dataset_context(self):
        request = self.get_atlas_request(f"/atlas/{self.dataset}/")
        response = BaseAtlasView.as_view()(request, dataset=self.dataset)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["dataset"], self.dataset)
        self.assertEqual(response.context_data["species"].common_name, "mouse")
        self.assertIn("dataset_dict", response.context_data)
        self.assertIn("links", response.context_data)

    def test_invalid_dataset_redirect(self):
        request = self.factory.get("/atlas/invalid/")
        response = BaseAtlasView.as_view()(request, dataset="invalid")

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("atlas"), response.url)


class AtlasInfoViewTest(BaseTestCase):
    def test_context_data_with_valid_dataset(self):
        request = self.factory.get("/atlas/{self.dataset}/")
        request.resolver_match = SimpleNamespace(url_name="atlas_info")

        response = AtlasInfoView.as_view()(request, dataset=self.dataset)
        context = response.context_data

        self.assertEqual(context["dataset"], self.dataset)
        self.assertIn("qc_metrics", context)

        for metric in context["qc_metrics"]:
            self.assertIn("title", metric)
            self.assertIn("values", metric)
