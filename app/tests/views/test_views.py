from django.test import TestCase, RequestFactory, override_settings
from django.http import Http404

from app.views import IndexView, DocumentationView


@override_settings(GHOST_INTERNAL_URL="https://biodiversitycellatals.org")
class IndexViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_homepage_context_and_template(self):
        request = self.factory.get("/")
        response = IndexView.as_view()(request)
        response.render()

        # Check context keys
        self.assertIn("dataset_dict", response.context_data)
        self.assertIn("posts", response.context_data)

        # Check posts keys
        expected_categories = [None, "publications", "meetings", "tutorials"]
        self.assertEqual(set(response.context_data["posts"].keys()), set(expected_categories))

        # Check dataset_dict is a dict
        self.assertIsInstance(response.context_data["dataset_dict"], dict)

        # Check response contains some text
        self.assertIn("<body", response.content.decode())


class DocumentationViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.docs_dir = DocumentationView.docs_dir

    def test_get_docs_index(self):
        request = self.factory.get("/docs/")
        response = DocumentationView.as_view()(request, page="_index")
        self.assertIn("<ul>", response.context_data["index"])

    def test_get_docs_dir(self):
        request = self.factory.get("/docs/tutorials/")
        response = DocumentationView.as_view()(request, page="tutorials")

        self.assertEqual(response.status_code, 200)
        self.assertIn("List of tutorials", response.context_data["content"])
        self.assertIn("Tutorials", response.context_data["index"])

        # Test breadcrumbs
        response.render()
        self.assertIn("Tutorials", response.content.decode())

    def test_get_docs_page(self):
        request = self.factory.get("/docs/tutorials/metacell.md")
        response = DocumentationView.as_view()(request, page="tutorials/metacell")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Metacell tutorial", response.context_data["content"])
        self.assertIn("Metacells", response.context_data["index"])

        metadata = response.context_data["metadata"]
        self.assertIn("title", metadata.keys())
        self.assertIn("linkTitle", metadata.keys())

    def test_get_context_data_404(self):
        # Test 404 on non-existing page
        request = self.factory.get("/docs/random-page/")
        with self.assertRaises(Http404):
            DocumentationView.as_view()(request, page="random-page")
