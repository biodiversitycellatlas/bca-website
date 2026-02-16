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
        self.assertContains(response, self.mouse)

        self.assertContains(response, "Division")
        self.assertContains(response, "Kingdom")
        self.assertContains(response, "Phylum")

        # Check if contains links for all the species datasets
        self.assertContains(response, "Datasets")
        for d in self.mouse.datasets.all():
            self.assertContains(response, d.get_html_link())

    def test_species_detail(self):
        response = self.client.get(f"/entry/species/{self.mouse}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mouse)
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

    def test_gene_list_by_species(self):
        response = self.client.get(f"/entry/gene/{self.mouse.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mouse.get_html_link())

    def test_gene_detail(self):
        response = self.client.get(f"/entry/gene/{self.mouse.slug}/{self.brca1.name}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mouse.get_named_html_link())

        # Check datasets
        self.assertContains(response, "BCA datasets")
        for d in self.mouse.datasets.all():
            self.assertContains(response, d)


class GeneListViewTests(DataTestCase):
    def test_genelist_list(self):
        response = self.client.get("/entry/gene-list/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.gene_list.get_html_link())
        self.assertContains(response, self.gene_list.description)
        self.assertContains(response, self.gene_list.genes.count())

    def test_genelist_detail(self):
        response = self.client.get(f"/entry/gene-list/{self.gene_list.name}/")
        self.assertEqual(response.status_code, 200)

        # Check genes
        self.assertContains(response, self.mouse)
        for g in self.gene_list.genes.all():
            self.assertContains(response, g.get_html_link())
            self.assertContains(response, g.get_domain_html_links())

    def test_genelist_detail_by_species(self):
        response = self.client.get(f"/entry/gene-list/{self.gene_list.name}/{self.mouse.slug}/")
        self.assertEqual(response.status_code, 200)

        # Check genes
        self.assertContains(response, self.mouse)
        for g in self.gene_list.genes.all():
            self.assertContains(response, g.get_html_link())
            self.assertContains(response, g.get_domain_html_links())


class GeneModuleViewTests(DataTestCase):
    def test_module_list(self):
        response = self.client.get("/entry/gene-module/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.adult_mouse)

    def test_module_list_by_species(self):
        response = self.client.get(f"/entry/gene-module/{self.adult_mouse.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.adult_mouse)

    def test_module_detail(self):
        response = self.client.get(f"/entry/gene-module/{self.adult_mouse.slug}/{self.gene_module.name}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.adult_mouse.get_html_link())

        # Check gene module
        self.assertContains(response, self.gene_module.name)
        self.assertContains(response, "Membership score")
        membership_score = self.gene_module.membership.get(gene=self.brca1).membership_score
        self.assertContains(response, membership_score)

        # Check for the expected gene and domains
        self.assertContains(response, self.brca1.get_html_link())
        self.assertContains(response, self.brca1.get_domain_html_links())


class DomainViewTests(DataTestCase):
    def test_domain_list(self):
        response = self.client.get("/entry/domain/")
        self.assertEqual(response.status_code, 200)

    def test_domain_detail(self):
        response = self.client.get(f"/entry/domain/{self.brca1_domains[0]}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mouse)

        # Check for the expected gene and domains
        self.assertContains(response, self.brca1.get_html_link())
        for domain in self.brca1_domains:
            self.assertContains(response, domain.get_html_link())


class OrthogroupViewTests(DataTestCase):
    def test_orthogroup_list(self):
        # List all orthogroups
        response = self.client.get("/entry/orthogroup/")
        self.assertEqual(response.status_code, 200)

        # Check orthologs
        orthologs = self.mouse.orthologs.first().orthologs.all()
        self.assertContains(response, orthologs.first().get_html_link())
        self.assertContains(response, "Number of orthologs")
        self.assertContains(response, orthologs.count())

    def test_orthogroup_detail(self):
        # List orthologs from a specific orthogroup
        response = self.client.get(f"/entry/orthogroup/{self.mouse.orthologs.first().orthogroup}/")
        self.assertEqual(response.status_code, 200)

        orthologs = self.mouse.orthologs.first().orthologs.all()
        for o in orthologs:
            self.assertContains(response, o.gene.get_html_link())
            self.assertContains(response, o.gene.get_domain_html_links())
            self.assertContains(response, o.gene.species)
