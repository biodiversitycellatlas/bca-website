from django.test import TestCase, RequestFactory
from django.http import Http404

from ..views import DocumentationView


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
