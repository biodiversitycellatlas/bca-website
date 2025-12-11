"""Miscellaneous views for health checks, downloads, errors, and static pages."""

import os
from pathlib import Path

from django.core.cache import cache
from django.conf import settings
from django.http import FileResponse, JsonResponse, Http404
from django.views import View
from django.views.generic import DetailView, TemplateView
from django.urls import reverse

from ..models import Dataset, SpeciesFile, Species
from ..templatetags.bca_website_links import bca_url, github_url
from ..utils import get_dataset_dict, get_species_dict
from ..utils.blog import get_latest_posts
from ..utils.markdown import MarkdownPage

class IndexView(TemplateView):
    """Homepage."""

    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        """Add dataset dictionary to context."""
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()

        categories = ["latest", "publications", "meetings", "tutorials"]
        posts = {c: get_latest_posts(tag=c if c != "latest" else None) for c in categories}
        context["posts"] = posts
        return context


class HealthView(View):
    """Health check endpoint."""

    def get(self, request, *args, **kwargs):
        """Return a 200 OK status in JSON."""
        return JsonResponse({"status": "ok"})


class RobotsView(TemplateView):
    """The robots.txt page."""

    template_name = "robots.txt"
    content_type = "text/plain"


class Custom403View(TemplateView):
    """Custom 403 Forbidden error page."""

    template_name = "403.html"


class Custom404View(TemplateView):
    """Custom 404 Not Found error page."""

    template_name = "404.html"


class Custom500View(TemplateView):
    """Custom 500 Internal Server Error page."""

    template_name = "500.html"


class DownloadsView(TemplateView):
    """Page displaying downloadable datasets and species files."""

    template_name = "app/downloads.html"

    def get_context_data(self, **kwargs):
        """Add all species and datasets to context."""
        context = super().get_context_data(**kwargs)
        context["species_all"] = Species.objects.all()
        context["datasets_all"] = Dataset.objects.all()
        return context


class SpeciesFileDownloadView(DetailView):
    """Serve a downloadable file from the File model."""

    model = SpeciesFile

    def render_to_response(self, context, **response_kwargs):
        """Return file as attachment with original filename."""
        resp = FileResponse(self.object.file.open(), as_attachment=True, filename=self.object.filename)
        return resp


class AboutView(TemplateView):
    """About page with contact, legal, and license info."""

    template_name = "app/about.html"

    def get_context_data(self, **kwargs):
        """Add structured info sections to context."""
        context = super().get_context_data(**kwargs)
        context["info"] = {
            "contact": [
                {"url": settings.FEEDBACK_URL, "icon": "fa-envelope", "label": "Email"},
                {
                    "url": github_url(),
                    "icon": "fa-brands fa-github",
                    "label": "Source code",
                },
                {
                    "url": github_url("issues/new"),
                    "icon": "fa-bug",
                    "label": "Bug reports",
                },
            ],
            "legal": [
                {
                    "url": bca_url("legal"),
                    "icon": "fa-shield-halved",
                    "label": "Legal Notice & Privacy Policy",
                },
                {
                    "url": bca_url("cookies"),
                    "icon": "fa-cookie-bite",
                    "label": "Cookies policy",
                },
            ],
            "licenses": [
                {
                    "url": github_url("blob/main/LICENSE"),
                    "icon": "fa-kiwi-bird",
                    "label": "BCA website",
                },
                {
                    "url": "https://fontawesome.com/license/free",
                    "icon": "fa-brands fa-font-awesome",
                    "label": "Icons by Font Awesome",
                },
                {
                    "url": "https://fonts.google.com/specimen/Rubik/license",
                    "icon": "fa-pen-nib",
                    "label": "Rubik font by Google Fonts",
                },
            ],
        }
        return context


def get_validated_cache(key, validation):
    cached = cache.get(key)
    if cached is not None:
        data, cached_validation = cached
        if validation == cached_validation:
            return data
    return None

def set_validated_cache(key, validation, data, timeout=24 * 60 * 60):
    cache.set(key, (data, validation), timeout=timeout)

class DocumentationView(TemplateView):
    """Documentation pages rendered from Markdown files."""

    template_name = "app/docs.html"
    docs_dir = "app/docs"

    def fetch_all_pages(self):
        pages = []
        for root, dirs, files in os.walk(self.docs_dir):
            for f in files:
                if f.endswith(".md"):
                    path = os.path.relpath(os.path.join(root, f), self.docs_dir)
                    pages.append(path.replace("\\", "/"))
        return pages

    def fetch_docs_pages(self):
        docs_path = Path(self.docs_dir)
        mtime = docs_path.stat().st_mtime
        key = "docs_pages"

        # Validate cache based on modified time of directory
        pages = get_validated_cache(key, mtime)
        if pages is not None:
            return pages

        pages = []
        #for root, dirs, files in os.walk(self.docs_dir):
        #    for f in files:
        #        if f.endswith(".md"):
        #            path = os.path.join(self.docs_dir, f)
        #            metadata = MarkdownPage(path).get_metadata()
        #            pages.append(Path(path).as_posix())
        for file_path in docs_path.rglob("*.md"):
            rel_path = file_path.relative_to(docs_path).as_posix()
            metadata = MarkdownPage(file_path).get_metadata()  # if needed
            pages.append(rel_path)

        raise ValueError(pages)
        set_validated_cache(key, mtime, pages)
        return pages

    def get_context_data(self, **kwargs):
        """Render HTML from Markdown files in hierarchy."""
        context = super().get_context_data(**kwargs)
        page = kwargs.get("page", "_index")
        file_path = os.path.join(self.docs_dir, f"{page}.md")

        if not os.path.exists(file_path):
            file_path = os.path.join(self.docs_dir, page, "_index.md")

        if os.path.exists(file_path):
            md = MarkdownPage(file_path)
            context["content"] = md.get_html()
            context["toc"] = md.get_toc()
            context["metadata"] = md.get_metadata()
            context["pygments_css"] = md.get_css()
        else:
            raise Http404()

        context["index"] = self.fetch_docs_pages()
        return context


class SearchView(TemplateView):
    """Search page for querying cell markers and datasets."""

    template_name = "app/search.html"

    def get_context_data(self, **kwargs):
        """Add dataset dictionary and search query to context."""
        context = super().get_context_data(**kwargs)
        context["species_dict"] = get_species_dict()

        query = self.request.GET
        if query:
            context["query"] = query
        return context
