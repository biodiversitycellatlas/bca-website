"""Test miscellaneous views."""

import ssl
import io
import os

from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.http import FileResponse

from app.views import DocumentationView
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
