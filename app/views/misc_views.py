from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.views import View
from django.views.generic import DetailView, TemplateView

from ..models import Dataset, File, Species
from ..templatetags.bca_website_links import bca_url
from ..utils import get_dataset, get_dataset_dict


class IndexView(TemplateView):
    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()
        return context


class HealthView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"})


class DownloadsView(TemplateView):
    template_name = "app/downloads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["species_all"] = Species.objects.all()
        context["datasets_all"] = Dataset.objects.all()
        return context


class FileDownloadView(DetailView):
    """
    Downloads the file with specified filename from `File` model.
    """

    model = File

    def render_to_response(self, context, **response_kwargs):
        resp = FileResponse(
            self.object.file.open(), as_attachment=True, filename=self.object.filename
        )
        return resp


class AboutView(TemplateView):
    template_name = "app/about.html"

    def get_context_data(self, **kwargs):
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


class SearchView(TemplateView):
    template_name = "app/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()
        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        if query:
            context["query"] = query
        return context
