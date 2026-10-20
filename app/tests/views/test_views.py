"""Test miscellaneous views."""

import json
import ssl
import io
import os

from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from bs4 import BeautifulSoup
from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.http import FileResponse

from app.models import Dataset
from app.utils import bioschemas
from app.views import DocumentationView
from app.tests.test_utils import assert_conforms
from app.tests.views.test_atlas_views import DataTestCase


@override_settings(GHOST_INTERNAL_URL="https://biodiversitycellatlas.org")
class IndexViewTest(DataTestCase):
    @classmethod
    def setUpTestData(cls):
        # Disable SSL verification to fetch data
        ssl._create_default_https_context = ssl._create_unverified_context
        super().setUpTestData()

    def test_homepage(self):
        # Suppress stdout/stderr during feed fetch to avoid 404 errors
        f = io.StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            response = self.client.get("/")

        assert "dataset_dict" in response.context
        assert "posts" in response.context

        # Check context keys
        assert "dataset_dict" in response.context
        assert "posts" in response.context

        # Check posts keys
        categories = ["latest", "publications", "meetings", "tutorials"]
        assert set(response.context["posts"].keys()) == set(categories)

        # Check dataset_dict is a dict
        assert isinstance(response.context["dataset_dict"], dict)

        # Check response contains some text
        assert "<body" in response.content.decode()


class TestStatusViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

    def test_health_json(self):
        response = self.client.get("/health/")
        assert response.status_code == 200
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_robots(self):
        response = self.client.get("/robots.txt")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert "User-agent" in response.content.decode()

    def test_403(self):
        response = self.client.get("/403/")
        assert response.status_code == 403
        self.assertTemplateUsed(response, "403.html")

    def test_404(self):
        response = self.client.get("/404/")
        assert response.status_code == 404
        self.assertTemplateUsed(response, "404.html")

    def test_random_404(self):
        response = self.client.get("/some-random-page/")
        assert response.status_code == 404
        self.assertTemplateUsed(response, "404.html")

    def test_500(self):
        response = self.client.get("/500/")
        assert response.status_code == 500
        self.assertTemplateUsed(response, "500.html")


class TestDownloadsView(TestCase):
    def test_downloads(self):
        response = self.client.get("/downloads/")
        assert response.status_code == 200
        assert "species_all" in response.context
        assert "datasets_all" in response.context


class SpeciesFileDownloadViewTests(DataTestCase):
    def test_file_download(self):
        response = self.client.get("/downloads/mus-musculus-proteome/")
        assert response.status_code == 200
        assert isinstance(response, FileResponse)

        filename = self.mouse_fasta.filename
        assert response.get("Content-Disposition") == f'attachment; filename="{filename}"'

        # Test file content
        expected = (">Brca1\nMACDEFGHIK\nLMNPQRSTVW\n>Brca2\nMACDEFGHIK\n").encode("utf-8")
        content = b"".join(response.streaming_content)
        assert content == expected


class TestDocumentationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.docs_dir = DocumentationView.docs_dir

    def test_docs_index(self):
        response = self.client.get("/docs/")
        assert response.status_code == 200
        assert "<ul>" in response.context["index"]

    def test_docs_dir(self):
        response = self.client.get("/docs/tutorials/")
        assert response.status_code == 200
        assert "List of tutorials" in response.context["content"]
        assert "Tutorials" in response.context["index"]

        # Test breadcrumbs
        assert "breadcrumb-nav" in response.content.decode()

    def test_docs_page(self):
        response = self.client.get("/docs/tutorials/metacell/")
        assert response.status_code == 200
        assert "Metacell tutorial" in response.context["content"]
        assert "Metacells" in response.context["index"]

        metadata = response.context["metadata"]
        assert "title" in metadata.keys()
        assert "linkTitle" in metadata.keys()

    def test_404(self):
        # Test 404 on non-existing page
        response = self.client.get("/docs/random-page/")
        assert response.status_code == 404


class TestAboutView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

    def test_about_view_context(self):
        response = self.client.get("/about/")
        assert response.status_code == 200
        assert "info" in response.context

        info = response.context["info"]

        # Check main sections exist
        assert "contact" in info
        assert "licenses" in info

        # Each section is a non-empty list of link items
        for section in info.values():
            assert section
            for item in section:
                assert isinstance(item["url"], str)
                assert isinstance(item["label"], str)
                assert isinstance(item["icon"], str)

        # Contact section links to the feedback email
        assert info["contact"][0]["url"] == settings.FEEDBACK_URL

    def test_last_updated(self):
        response = self.client.get("/about/")
        assert response.status_code == 200

        # Check if last modified time for template is correctly being used
        template = response.templates[0].origin.name

        mtime = os.path.getmtime(template)
        mtime_str = datetime.fromtimestamp(mtime).strftime("%d %B %Y")

        content = response.content.decode()
        assert "Last updated" in content
        assert mtime_str in content

    def test_licenses(self):
        response = self.client.get("/about/")
        assert response.status_code == 200
        content = response.content.decode()

        collapse_start = content.index('id="collapsed-items-')
        before_collapse = content[:collapse_start]
        after_collapse = content[collapse_start:]

        # A toggle is shown upfront, with links visible before it and hidden after it
        assert "BCA website (Apache-2.0)" in before_collapse
        assert "BCA data (CC BY 4.0)" in before_collapse
        assert 'data-bs-toggle="collapse"' in before_collapse
        assert "<li" in before_collapse
        assert "<li" in after_collapse
        assert "Rubik" in after_collapse


class SearchViewTest(DataTestCase):
    def test_search_view_context_without_query(self):
        response = self.client.get("/search/")
        assert response.status_code == 200
        assert "species_dict" in response.context
        assert "query" not in response.context

    def test_search_view_context_with_query(self):
        response = self.client.get("/search/", {"q": "test"})
        assert response.status_code == 200
        assert "species_dict" in response.context
        assert "query" in response.context
        assert response.context["query"]["q"] == "test"


class BioschemasViewTest(DataTestCase):
    """Check that each candidate page serves parseable, conformant JSON-LD."""

    def jsonld_scripts(self, content):
        """Return the JSON-LD ``<script>`` tags found in `content`."""
        return BeautifulSoup(content, "html.parser").find_all("script", type="application/ld+json")

    def payloads(self, url):
        """Return the parsed JSON-LD blocks served by `url`."""
        response = self.client.get(url)
        assert response.status_code == 200, f"{url} returned {response.status_code}"
        scripts = self.jsonld_scripts(response.content)
        assert scripts, f"{url} served no JSON-LD"
        return [json.loads(script.string) for script in scripts]

    def assert_page(self, url, type_, profile=None):
        """Assert `url` serves exactly one JSON-LD block of the expected type."""
        payloads = self.payloads(url)
        assert len(payloads) == 1, f"{url} served {len(payloads)} JSON-LD blocks"

        payload = payloads[0]
        assert payload["@context"] == bioschemas.CONTEXT
        assert payload["@type"] == type_
        if profile:
            assert_conforms(payload, profile)
        return payload

    def test_home_serves_a_data_catalog(self):
        self.assert_page("/", "DataCatalog", "DataCatalog")

    def test_downloads_serves_a_data_catalog(self):
        payload = self.assert_page("/downloads/", "DataCatalog", "DataCatalog")
        names = [each["name"] for each in payload["distribution"]]
        assert self.mouse_fasta.label in names

    def test_species_detail_serves_a_taxon(self):
        payload = self.assert_page(f"/entry/species/{self.mouse}/", "Taxon", "Taxon")
        assert payload["name"] == "Mus musculus"
        assert payload["vernacularName"] == "mouse"

    def test_species_list_serves_a_collection_page(self):
        payload = self.assert_page("/entry/species/", "CollectionPage")
        names = [each["item"]["name"] for each in payload["mainEntity"]["itemListElement"]]
        assert "Mus musculus" in names

    def test_dataset_list_serves_a_data_catalog(self):
        payload = self.assert_page("/entry/dataset/", "DataCatalog", "DataCatalog")
        assert len(payload["dataset"]) == Dataset.objects.count()
        for each in payload["dataset"]:
            assert_conforms(each, "Dataset")

    def test_gene_detail_serves_a_gene(self):
        payload = self.assert_page(f"/entry/gene/{self.mouse.slug}/{self.brca1.name}/", "Gene", "Gene")
        assert payload["name"] == "Brca1"
        assert payload["taxonomicRange"]["name"] == "Mus musculus"
        assert {each["name"] for each in payload["hasBioChemEntityPart"]} == {
            domain.name for domain in self.brca1_domains
        }

    def test_gene_list_serves_a_collection_page(self):
        payload = self.assert_page(f"/entry/gene/{self.mouse.slug}/", "CollectionPage")
        assert payload["mainEntity"]["numberOfItems"] == self.mouse.genes.count()

    def test_atlas_dataset_serves_a_dataset(self):
        payload = self.assert_page(f"/atlas/{self.adult_mouse.slug}/", "Dataset", "Dataset")
        assert payload["name"] == str(self.adult_mouse)
        assert payload["about"]["name"] == "Mus musculus"

    def test_atlas_gene_page_points_at_the_canonical_gene(self):
        url = f"/atlas/{self.adult_mouse.slug}/gene/{self.brca1.name}/"
        payload = self.assert_page(url, "Gene", "Gene")
        assert payload["url"].endswith(self.brca1.get_absolute_url())
        assert payload["mainEntityOfPage"].endswith(url)

    def test_atlas_gene_page_is_silent_for_an_unknown_gene(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/nope/")
        assert response.status_code == 200
        assert not self.jsonld_scripts(response.content)

    def test_pages_without_a_matching_profile_serve_no_jsonld(self):
        """Tier 3 pages are deliberately left without structured data."""
        for url in (
            "/entry/",
            "/entry/domain/",
            f"/entry/domain/{self.brca1_domains[0].name}/",
            "/entry/orthogroup/",
            f"/entry/orthogroup/{self.og1.name}/",
            f"/entry/gene-module/{self.adult_mouse.slug}/{self.gene_module.name}/",
            "/about/",
            "/search/",
        ):
            response = self.client.get(url)
            assert response.status_code == 200, f"{url} returned {response.status_code}"
            assert not self.jsonld_scripts(response.content), f"{url} unexpectedly served JSON-LD"
