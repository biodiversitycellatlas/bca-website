import ssl
import io
import os

from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from django.test import TestCase, Client, override_settings
from django.conf import settings

from app.views import DocumentationView
from app.tests.views.test_atlas_views import BaseTestCase


@override_settings(GHOST_INTERNAL_URL="https://biodiversitycellatlas.org")
class IndexViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Disable SSL verification to fetch data
        ssl._create_default_https_context = ssl._create_unverified_context
        cls.client = Client()

    def test_homepage_context(self):
        # Suppress stdout/stderr during feed fetch to avoid 404 errors
        f = io.StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            response = self.client.get("/")

        self.assertIn("dataset_dict", response.context)
        self.assertIn("posts", response.context)

        # Check context keys
        self.assertIn("dataset_dict", response.context)
        self.assertIn("posts", response.context)

        # Check posts keys
        categories = [None, "publications", "meetings", "tutorials"]
        self.assertEqual(set(response.context["posts"].keys()), set(categories))

        # Check dataset_dict is a dict
        self.assertIsInstance(response.context["dataset_dict"], dict)

        # Check response contains some text
        self.assertIn("<body", response.content.decode())


class DocumentationViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.docs_dir = DocumentationView.docs_dir

    def test_docs_index(self):
        response = self.client.get("/docs/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<ul>", response.context["index"])

    def test_docs_dir(self):
        response = self.client.get("/docs/tutorials/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("List of tutorials", response.context["content"])
        self.assertIn("Tutorials", response.context["index"])

        # Test breadcrumbs
        self.assertIn("breadcrumb-nav", response.content.decode())

    def test_docs_page(self):
        response = self.client.get("/docs/tutorials/metacell/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Metacell tutorial", response.context["content"])
        self.assertIn("Metacells", response.context["index"])

        metadata = response.context["metadata"]
        self.assertIn("title", metadata.keys())
        self.assertIn("linkTitle", metadata.keys())

    def test_404(self):
        # Test 404 on non-existing page
        response = self.client.get("/docs/random-page/")
        self.assertEqual(response.status_code, 404)


class AboutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.response = self.client.get("/about/")

    def test_about_view_context(self):
        # Check that context contains "info"
        self.assertIn("info", self.response.context)
        info = self.response.context["info"]

        # Check main sections exist
        self.assertIn("contact", info)
        self.assertIn("legal", info)
        self.assertIn("licenses", info)

        # Check that contact section contains the Email entry
        email_entry = info["contact"][0]
        self.assertEqual(email_entry["url"], settings.FEEDBACK_URL)

        # Check licenses section
        fa_entry = next((x for x in info["licenses"] if "Font Awesome" in x["label"]), None)
        self.assertIsNotNone(fa_entry)

        rubik_entry = next((x for x in info["licenses"] if "Rubik font" in x["label"]), None)
        self.assertIsNotNone(rubik_entry)

        # Check URLs
        for section in info.values():
            for item in section:
                self.assertIsInstance(item["url"], str)
                self.assertIsInstance(item["label"], str)
                self.assertIsInstance(item["icon"], str)

    def test_last_updated(self):
        # Check if last modified time for template is correctly being used
        template = self.response.templates[0].origin.name
        mtime = os.path.getmtime(template)
        mtime_str = datetime.fromtimestamp(mtime).strftime("%d %B %Y")

        content = self.response.content.decode()
        self.assertIn("Last updated", content)
        self.assertIn(mtime_str, content)


class SearchViewTest(BaseTestCase):
    def test_search_view_context_without_query(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("species_dict", response.context)
        self.assertNotIn("query", response.context)

    def test_search_view_context_with_query(self):
        response = self.client.get("/search/", {"q": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("species_dict", response.context)
        self.assertIn("query", response.context)
        self.assertEqual(response.context["query"]["q"], "test")
