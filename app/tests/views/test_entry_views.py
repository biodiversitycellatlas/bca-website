"""Test database entry views."""

from app.tests.views.utils import DataTestCase


class EntryViewTests(DataTestCase):
    def test_index(self):
        response = self.client.get("/entry/")
        self.assertEqual(response.status_code, 200)


class SpeciesViewTests(DataTestCase):
    def test_species_list(self):
        response = self.client.get("/entry/species/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.species)

        self.assertContains(response, "Division")
        self.assertContains(response, "Kingdom")
        self.assertContains(response, "Phylum")

        # Check if contains links for all the species datasets
        self.assertContains(response, "Datasets")
        for d in self.species.datasets.all():
            self.assertContains(response, d.get_html_link())

    def test_species_detail(self):
        response = self.client.get(f"/entry/species/{self.species}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.species)
        self.assertContains(response, "Metadata")
        self.assertContains(response, "Species data")
        self.assertContains(response, "File download")


class DatasetViewTests(DataTestCase):
    def test_dataset_list(self):
        response = self.client.get("/entry/dataset/")
        self.assertEqual(response.status_code, 200)


class GeneViewTests(DataTestCase):
    def test_gene_list(self):
        response = self.client.get("/entry/gene/")
        self.assertEqual(response.status_code, 200)


class GeneListViewTests(DataTestCase):
    def test_genelist_list(self):
        response = self.client.get("/entry/gene-list/")
        self.assertEqual(response.status_code, 200)


class GeneModuleViewTests(DataTestCase):
    def test_module_list(self):
        response = self.client.get("/entry/gene-module/")
        self.assertEqual(response.status_code, 200)


class DomainViewTests(DataTestCase):
    def test_domain_list(self):
        response = self.client.get("/entry/domain/")
        self.assertEqual(response.status_code, 200)


class OrthogroupViewTests(DataTestCase):
    def test_orthogroup_list(self):
        response = self.client.get("/entry/orthogroup/")
        self.assertEqual(response.status_code, 200)
