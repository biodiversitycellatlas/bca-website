from django.shortcuts import redirect, reverse
from django.views.generic import TemplateView
from django.db.models import Q

from ..models import Dataset
from ..utils import get_dataset_dict, get_metacell_dict, get_cell_atlas_links

import random


class AtlasView(TemplateView):
    template_name = "app/atlas/atlas.html"

    def get_species_icon(self, species=None):
        if species is None:
            species = [
                "frog", "mosquito", "cow", "otter", "kiwi-bird", "shrimp", "crow",
                "dove", "fish-fins", "cat", "locust", "tree", "spider", "hippo"
            ]
            species = random.choice(species)
        return species

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["icon"] = self.get_species_icon()
        context["dataset_dict"] = get_dataset_dict()

        query = self.request.GET
        if query and query.get('dataset'):
            dataset = query['dataset']
            if isinstance(dataset, Dataset):
                context['dataset'] = dataset
            else:
                # Warn that dataset is not available in the database
                context['warning'] = {
                    'title': f'Invalid dataset <code>{dataset}</code>!',
                    'description': f"Please check available datasets in the search box above."
                }

        # Prepare Cell Atlas links
        url_name = self.request.resolver_match.url_name
        context['links'] = get_cell_atlas_links(url_name)
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

        d = get_dataset(dataset)
        if isinstance(d, Dataset):
            context["dataset"] = d
            context["species"] = d.species
            context["dataset_dict"] = get_dataset_dict()

            # Prepare Cell Atlas links
            url_name = self.request.resolver_match.url_name
            context["links"] = get_cell_atlas_links(url_name, d)
        else:
            context["dataset"] = dataset

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
