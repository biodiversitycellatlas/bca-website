"""Miscellaneous views for health checks, downloads, errors, and static pages."""

import os

from django.conf import settings
from django.http import FileResponse, JsonResponse, Http404
from django.views import View
from django.views.generic import DetailView, TemplateView
from django.urls import reverse
from django.templatetags.static import static
from django.shortcuts import render

from ..models import Dataset, SpeciesFile, Species, SingleCell
from ..templatetags.bca_website_links import bca_url, github_url
from ..utils import get_dataset_dict, get_species_dict
from ..utils.blog import get_latest_posts
from ..utils.markdown import MarkdownPage
from ..utils.cache import get_validated_cache, set_validated_cache


class IndexView(TemplateView):
    """Homepage."""

    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        """Add dataset dictionary to context."""
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()

        # Get examples for feature links
        example = Dataset.objects.first()
        context["example_dataset"] = example
        context["example_gene"] = (
            example.species.genes.first()
            if example and example.species and example.species.genes
            else None
        )

        # Fetch number of cells, species and datasets
        counter = {
            "datasets": Dataset.objects.count(),
            "species": Species.objects.count(),
            "cells": SingleCell.objects.count(),
        }
        context["counter"] = counter

        # Fetch latest blog posts
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

    def get(self, request, *args, **kwargs):
        """Return a 403 error page with the corresponding status."""
        return render(request, "403.html", status=403)


class Custom404View(View):
    """Custom 404 Not Found error page."""

    def get(self, request, *args, **kwargs):
        """Return a 404 error page with the corresponding status."""
        return render(request, "404.html", status=404)


class Custom500View(View):
    """Custom 500 Internal Server Error page."""

    def get(self, request, *args, **kwargs):
        """Return a 500 error page with the corresponding status."""
        return render(request, "500.html", status=500)


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


class DocumentationView(TemplateView):
    """Documentation pages rendered from Markdown files."""

    template_name = "app/docs.html"
    docs_dir = "app/static/docs"
    index = "_index"
    index_file = f"{index}.md"

    def generate_docs_link(self, dir, filename=None):
        """Generate link to documentation page."""
        if filename is not None and filename.endswith(".md"):
            filename = os.path.splitext(filename)[0]
        real_path = os.path.join(dir, filename or "")

        link = os.path.relpath(real_path, self.docs_dir)
        link = reverse("docs", kwargs={"page": link})
        return link

    def generate_docs_link_title(self, path, default=None):
        index_path = os.path.join(path, self.index_file)
        if os.path.isfile(path):
            # Read title from file's metadata
            meta = MarkdownPage(path).metadata
            title = meta.get("linkTitle") or meta.get("title")
        elif os.path.isdir(path) and os.path.isfile(index_path):
            # Read title from index file's metadata
            title = self.generate_docs_link_title(index_path)
        else:
            # Create title from default or path
            default = default or os.path.basename(path)
            title = None

        if title is None and default is not None:
            title = default.replace(".md", "").capitalize()

        return title

    def build_html_index(self, path=None, head=True):
        path = path or self.docs_dir

        # Ignore hidden files
        entries = sorted(f for f in os.listdir(path) if not f.startswith("."))

        html = ""
        for name in entries:
            this_path = os.path.join(path, name)

            if os.path.isdir(this_path):
                if name == "images":
                    continue
                branch = self.build_html_index(this_path, head=False)
                html += f"<li>{branch}</li>"
            elif name != self.index_file:
                link = self.generate_docs_link(path, name)
                title = self.generate_docs_link_title(this_path)
                html += f'<li><a href="{link}">{title}</a></li>'

        html = f"<ul>{html}</ul>"

        # Wrap directory name with metadata from _index.md
        if head:
            # Top level directory
            pass
        elif self.index_file in entries:
            title = self.generate_docs_link_title(path)
            link = self.generate_docs_link(path)
            html = f'<a href="{link}">{title}</a>' + html
        else:
            title = self.generate_docs_link_title(path)
            title = os.path.basename(path).capitalize()
            html = title + html
        return html

    def get_html_index(self):
        # Cache HTML index using last modified time of docs dir
        key = "docs_index"
        validation = os.path.getmtime(self.docs_dir)

        cached = get_validated_cache(key, validation)
        if cached is None:
            cached = self.build_html_index()
            set_validated_cache(key, validation, cached)
        return cached

    def get_context_data(self, **kwargs):
        """Render HTML from Markdown files in hierarchy."""

        context = super().get_context_data(**kwargs)
        page = kwargs.get("page", self.index)
        file_path = os.path.join(self.docs_dir, f"{page}.md")

        if not os.path.exists(file_path):
            file_path = os.path.join(self.docs_dir, page, self.index_file)

        if os.path.exists(file_path):
            # Fetch corresponding static location
            static_path = self.request.path
            if os.path.basename(file_path) != self.index_file:
                # If not index page, go back once to fix path
                static_path = os.path.join(static_path, "..")
            static_dir = static(static_path.lstrip("/"))

            # Parse Markdown page
            md = MarkdownPage(file_path, static_dir=static_dir)
            context["content"] = md.html
            context["toc"] = md.toc
            context["metadata"] = md.metadata
            context["pygments_css"] = md.get_pygment_css()
            context["action_links"] = md.get_action_links()
        else:
            raise Http404()

        context["index"] = self.get_html_index()
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
