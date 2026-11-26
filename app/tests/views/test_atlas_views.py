"""Test Cell Atlas views."""

from django.urls import reverse

from app.models import Gene, MetacellTypeSimilarity
from app.tests.views.utils import DataTestCase
from app.views import AtlasInfoView, AtlasView


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

    def test_query_dataset_redirect(self):
        response = self.client.get(f"/atlas/?dataset={self.adult_mouse.slug}")
        assert response.status_code == 302
        assert response.url == reverse("atlas_info", args=[self.adult_mouse.slug])


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

    def test_dataset_with_unnanotated_metacells(self):
        self.adult_mouse.metacells.create(name="1")
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

    def test_markers_with_nonnumeric_metacell_names(self):
        self.adult_mouse.metacells.create(name="acrmil01_MC_00204")
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/markers/?metacells=acrmil01_MC_00204")
        assert response.status_code == 200
        assert response.context["metacells"] == ["acrmil01_MC_00204"]


class AtlasCompareViewTest(DataTestCase):
    def test_gene_markers(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/compare/")
        assert response.status_code == 200

    def test_compare_datasets_filtered(self):
        human_dataset = self.human.datasets.create(name="fetal")
        t1 = self.adult_mouse.metacell_types.create(name="t1")
        t2 = human_dataset.metacell_types.create(name="t2")
        MetacellTypeSimilarity.objects.create(metacelltype=t1, metacelltype2=t2, samap_score=0.8)
        human_dataset.gene_modules.create(name="blue").genes.add(self.brca1_human)

        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/compare/")
        dict_ = response.context["compare_dataset_dict"]
        datasets = {elem["dataset"] for elems in dict_.values() for elem in elems}

        assert human_dataset in datasets
        assert self.baby_mouse not in datasets


class AtlasCellTypeHierarchyViewTest(DataTestCase):
    def test_valid_dataset(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/hierarchy/")
        assert response.status_code == 200

        context = response.context
        assert context["dataset"] == self.adult_mouse
        assert context["species"] == self.mouse


class BaseAtlasViewTest(DataTestCase):
    def test_cell_atlas_links(self):
        """Check the Cell Atlas navigation links."""
        view = AtlasInfoView()

        with self.subTest(name="active entry"):
            # Current page is active and anchors to the top of the page
            links = view.get_cell_atlas_links("atlas_info", self.adult_mouse)
            link = next(link for link in links if link["url_view"] == "atlas_info")
            assert link["active"] is True
            assert link["href"] == "#top"
            assert link["disabled"] is False

            # Entries for other pages point to that page for the given dataset
            link = next(link for link in links if link["url_view"] == "atlas_hierarchy")
            assert link["active"] is False
            assert link["href"] == reverse("atlas_hierarchy", args=[self.adult_mouse.slug])

        with self.subTest(name="no dataset"):
            # No dataset selected: only the current page is active and others are disabled
            links = view.get_cell_atlas_links("atlas_info", None)
            for link in links:
                assert link["disabled"] is True
                if link["url_view"] != "atlas_info":
                    assert link["active"] is False
                    assert link["href"] == "#"
            active = next(link for link in links if link["url_view"] == "atlas_info")
            assert active["active"] is True
            assert active["href"] == "#top"

        # An unknown dataset slug falls back to the dataset index page
        with self.subTest(name="unknown dataset slug"):
            links = view.get_cell_atlas_links("atlas_info", "no-such-dataset")
            for link in links:
                if not link["active"]:
                    assert link["href"] == reverse("atlas")
