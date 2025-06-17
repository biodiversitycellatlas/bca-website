from django.http import Http404
from django.shortcuts import redirect, reverse
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView

from django.db.models import Q

from .models import Dataset
from .utils import get_dataset_dict, get_metacell_dict, get_dataset

import random


class IndexView(TemplateView):
    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()
        return context


class AtlasView(TemplateView):
    template_name = "app/atlas/atlas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["icon"] = random.choice(
            ["frog", "mosquito", "cow", "otter", "kiwi-bird", "shrimp", "crow",
            "dove", "fish-fins", "cat", "locust", "tree", "spider", "hippo"])
        context["dataset_dict"] = get_dataset_dict()

        query = self.request.GET
        if query and query.get('dataset'):
            dataset = query['dataset']
            if isinstance(dataset, Dataset):
                context['dataset'] = dataset
            else:
                # Warn that dataset is not available in the database
                context['warning'] = {
                    'title': f'Invalid dataset <code>{query['dataset']}</code>!',
                    'description': f"Please check available datasets in the search box above."
                }

        return context

    def get(self, request, *args, **kwargs):
        query = self.request.GET
        dataset = request.COOKIES.get('dataset') or query.get('dataset')

        if dataset and isinstance(dataset, Dataset):
            return redirect('atlas_info', dataset)
        else:
            return super().get(request, *args, **kwargs)


class BaseAtlasView(TemplateView):
    '''
    Base view for dataset-specific Cell Atlas pages.

    Redirects to standard Atlas view with a warning when passing a dataset not
    available in the database.
    '''
    model = Dataset
    template_name = "app/atlas/info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get URL query parameters
        query = self.request.GET
        context['query'] = query

        dataset = context["dataset"]

        try:
            dataset = get_dataset(dataset)
            context["dataset"] = dataset
            context["species"] = dataset.species
        except:
            context["dataset"] = dataset
            return context

        context["dataset_dict"] = get_dataset_dict()
        return context

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        dataset = context["dataset"]
        if not isinstance(dataset, Dataset):
            if dataset is None:
                dataset = 'invalid'
            return redirect(reverse('atlas') + '?dataset=' + dataset)
        return super().get(*args, **kwargs)


class AtlasInfoView(BaseAtlasView):
    template_name = "app/atlas/info.html"


class AtlasOverviewView(BaseAtlasView):
    template_name = "app/atlas/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = context['dataset']
        if not isinstance(dataset, Dataset):
            return context

        context['metacell_dict'] = get_metacell_dict(dataset)
        return context


class AtlasGeneView(BaseAtlasView):
    template_name = "app/atlas/gene.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = context.get('dataset')
        if not isinstance(dataset, Dataset):
            return context

        gene = context.get('gene')
        if gene:
            # Fetch information on selected gene
            obj = dataset.species.genes.filter(name=gene)
            if obj:
                context['gene'] = obj.first()
            else:
                # Throw a warning if gene does not exist
                context['gene'] = ''
                context['warning'] = {
                    'title': f'Invalid gene <code>{gene}</code>!',
                    'description': f"Please check available genes in the search box above."
                }
        return context

class AtlasPanelView(BaseAtlasView):
    template_name = "app/atlas/panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = context.get('dataset')
        if not isinstance(dataset, Dataset):
            return context

        context['metacell_dict'] = get_metacell_dict(dataset)
        return context


class AtlasMarkersView(BaseAtlasView):
    template_name = "app/atlas/markers.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = context["dataset"]
        if not isinstance(dataset, Dataset):
            return context

        context['metacell_dict'] = get_metacell_dict(dataset)

        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        if query:
            context['query'] = query
            if 'metacells' in query.keys():
                # get selected metacells
                metacells = query['metacells'].split(',')
                selected = list(dataset.metacells.filter(
                    Q(name__in=metacells) | Q(type__name__in=metacells)
                ).values_list('name', flat=True).distinct())
                selected = [int(s) for s in selected]
                selected.sort()

                context['metacells'] = selected
            else:
                context['warning'] = {
                    'title': 'Invalid URL!',
                    'description': f"There is no <code>metacells</code> parameter in your query: <code>{query.urlencode()}</code>"
                }
        return context


class AtlasCompareView(BaseAtlasView):
    template_name = "app/atlas/compare.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        dataset = context["dataset"]
        if not isinstance(dataset, Dataset):
            return context

        # Parse URL query parameters and get dataset to compare SAMap scores
        try:
            query = self.request.GET
            if query['dataset']:
                dataset2 = get_dataset(query['dataset'])
                context["dataset2"] = dataset2
                context["species"] = dataset2.species
        except:
            pass
        return context


class ComparisonView(TemplateView):
    template_name = "app/comparison.html"


class DownloadsView(TemplateView):
    template_name = "app/downloads.html"


class BlogView(TemplateView):
    template_name = "app/blog.html"


class AboutView(TemplateView):
    template_name = "app/about/about.html"


class CookiesView(TemplateView):
    template_name = "app/about/cookies.html"


class LegalView(TemplateView):
    template_name = "app/about/legal.html"


class SearchView(TemplateView):
    template_name = "app/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()
        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        if query:
            context['query'] = query
        return context
