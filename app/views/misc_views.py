"""Miscellaneous views for health checks, downloads, errors, and static pages."""

import os

from django.conf import settings
from django.http import FileResponse, JsonResponse, Http404
from django.views import View
from django.views.generic import DetailView, TemplateView

from ..models import Dataset, File, Species
from ..templatetags.bca_website_links import bca_url
from ..utils import (
    get_dataset_dict, get_species_dict, render_markdown, get_pygments_css
)


class IndexView(TemplateView):
    """Homepage."""

    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        """Add dataset dictionary to context."""
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()
        return context


class HealthView(View):
    """Health check endpoint."""

    def get(self, request, *args, **kwargs):
        """Return a 200 OK status in JSON."""
        return JsonResponse({"status": "ok"})


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


class FileDownloadView(DetailView):
    """Serve a downloadable file from the File model."""

    model = File

    def render_to_response(self, context, **response_kwargs):
        """Return file as attachment with original filename."""
        resp = FileResponse(
            self.object.file.open(), as_attachment=True, filename=self.object.filename
        )
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
                    "url": settings.GITHUB_URL,
                    "icon": "fa-brands fa-github",
                    "label": "Source code",
                },
                {
                    "url": settings.GITHUB_ISSUES_URL,
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
                    "url": "https://fontawesome.com/license/free",
                    "icon": "fa-brands fa-font-awesome",
                    "label": "Icons by Font Awesome",
                },
                {
                    "url": "https://fonts.google.com/specimen/Rubik/license",
                    "icon": "fa-book",
                    "label": "Rubik font by Google Fonts",
                },
            ],
        }
        return context


class ReferenceView(TemplateView):
    """Reference pages rendered from Markdown files."""

    template_name = "app/reference.html"
    reference_dir = "app/reference"

    def get_context_data(self, **kwargs):
        """Render HTML from Markdown files."""
        context = super().get_context_data(**kwargs)
        page = kwargs.get("page", "index")
        file_path = os.path.join(self.reference_dir, f"{page}.md")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            context["content"] = render_markdown(md_content)
            context["pygments_css"] = get_pygments_css()
        else:
            raise Http404()

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
