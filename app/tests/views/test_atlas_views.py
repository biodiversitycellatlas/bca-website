"""Test Cell Atlas views."""

from django.urls import reverse

from app.views import AtlasView
from app.models import Gene
from app.tests.views.utils import DataTestCase


class AtlasViewTest(DataTestCase):
    def test_atlas_view_basic(self):
        response = self.client.get("/atlas/")
        assert response.status_code == 200
        assert "icon" in response.context
        assert "dataset_dict" in response.context
        assert "links" in response.context

    def test_get_species_icon_random(self):
        icon = AtlasView().get_species_icon()
        assert isinstance(icon, str)

    def test_invalid_dataset_warning(self):
        response = self.client.get("/atlas/?dataset=invalid-dataset")
        assert "warning" in response.context
        assert "Invalid dataset" in response.context["warning"]["title"]

    def test_invalid_dataset_redirect(self):
        response = self.client.get("/atlas/invalid/")
        assert response.status_code == 302
        assert reverse("atlas") in response.url


class AtlasInfoViewTest(DataTestCase):
    def test_dataset(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/")
        assert response.status_code == 200

        context = response.context
        assert context["dataset"] == self.adult_mouse
        assert context["species"].common_name == "mouse"
        assert "dataset_dict" in context
        assert "links" in context

        # Test quality control metrics
        assert "qc_metrics" in context
        for metric in context["qc_metrics"]:
            assert "title" in metric
            assert "values" in metric


class AtlasOverviewViewTest(DataTestCase):
    def test_dataset(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/overview/")
        assert response.status_code == 200


class AtlasGeneViewTest(DataTestCase):
    def test_index(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/")
        assert response.status_code == 200
        assert "gene" in response.context
        assert response.context["gene"] == ""
        assert "warning" not in response.context

    def test_valid_gene(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/{self.brca1.name}/")
        assert response.status_code == 200
        assert "gene" in response.context
        assert isinstance(response.context["gene"], Gene)
        assert response.context["gene"].name == self.brca1.name

        # No warnings expected
        assert "warning" not in response.context

    def test_invalid_gene(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/invalid-gene/")
        assert response.status_code == 200
        assert response.context["gene"] == ""
        assert "warning" in response.context

        # Raise warning for invalid gene
        warning = response.context["warning"]
        assert "Invalid gene" in warning["title"]
        assert "Please check available genes" in warning["description"]


class AtlasPanelViewTest(DataTestCase):
    def test_gene_panel(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/panel/")
        assert response.status_code == 200
        assert "metacell_dict" in response.context


class AtlasModuleViewTest(DataTestCase):
    def test_gene_modules(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/modules/")
        assert response.status_code == 200
        assert "Module activity" in response.content.decode()


class AtlasMarkersViewTest(DataTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/markers/")
        assert response.status_code == 200
        assert "metacell_dict" in response.context


class AtlasCompareViewTest(DataTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/compare/")
        assert response.status_code == 200
