from django.http import FileResponse, Http404
from django.shortcuts import redirect, reverse
from django.views.generic import TemplateView, ListView, DetailView
from django.conf import settings
from django.db.models import Q

from .models import Dataset, Species, File, Gene, GeneModule, Ortholog
from .utils import (
    get_dataset_dict, get_metacell_dict, get_dataset, get_species_dict,
    get_cell_atlas_links, get_species, parse_gene_slug
)
from .templatetags.bca_website_links import bca_url

import random


class IndexView(TemplateView):
    template_name = "app/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset_dict"] = get_dataset_dict()
        return context


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


class EntryView(TemplateView):
    template_name = "app/entries/entry.html"


class EntrySpeciesListView(ListView):
    model = Species
    paginate_by = 20
    template_name = 'app/entries/species_list.html'


class EntrySpeciesDetailView(DetailView):
    model = Species
    template_name = 'app/entries/species_detail.html'
    slug_field = "scientific_name"
    slug_url_kwarg = "species"


class EntryDatasetListView(ListView):
    model = Dataset
    paginate_by = 20
    template_name = 'app/entries/dataset_list.html'


class FilteredListView(ListView):
    """ Allow filtering view by dataset or species. """
    filter_by = None

    def get_filter_function(self):
        if self.filter_by == 'dataset':
            return get_dataset
        elif self.filter_by == 'species':
            return get_species
        return None

    def get_queryset(self):
        qs = super().get_queryset()
        value = self.kwargs.get(self.filter_by)
        func = self.get_filter_function()
        if value and func:
            obj = func(value)
            qs = qs.filter(**{self.filter_by: obj})
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        value = self.kwargs.get(self.filter_by)
        func = self.get_filter_function()
        if value and func:
            context[self.filter_by] = func(value)
        return context


class EntryGeneListView(FilteredListView):
    model = Gene
    paginate_by = 20
    template_name = 'app/entries/gene_list.html'
    filter_by = 'species'


class EntryGeneDetailView(DetailView):
    model = Gene
    template_name = 'app/entries/gene_detail.html'
    slug_field = "name"
    slug_url_kwarg = "gene"


class EntryGeneModuleListView(FilteredListView):
    model = GeneModule
    paginate_by = 20
    template_name = 'app/entries/gene_module_list.html'
    filter_by = 'dataset'


class EntryGeneModuleDetailView(DetailView):
    model = GeneModule
    template_name = 'app/entries/gene_module_detail.html'
    slug_field = "name"
    slug_url_kwarg = "gene"


class EntryOrthogroupListView(ListView):
    model = Ortholog
    paginate_by = 20
    template_name = 'app/entries/orthogroup_list.html'

    def get_queryset(self):
        return super().get_queryset().order_by('orthogroup').distinct('orthogroup')


class EntryOrthogroupDetailView(DetailView):
    model = Ortholog
    template_name = 'app/entries/orthogroup_detail.html'
    slug_field = "orthogroup"
    slug_url_kwarg = "orthogroup"

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        slug = self.kwargs.get(self.slug_url_kwarg)
        return queryset.filter(**{self.slug_field: slug}).first()


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
            self.object.file.open(),
            as_attachment=True,
            filename=self.object.filename)
        return resp


class AboutView(TemplateView):
    template_name = "app/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['info'] = {
            'contact': [
                {
                    'url': settings.FEEDBACK_URL,
                    'icon': 'fa-envelope',
                    'label': 'Email'
                }, {
                    'url': settings.GITHUB_URL,
                    'icon': 'fa-brands fa-github',
                    'label': 'Source code'
                }, {
                    'url': settings.GITHUB_ISSUES_URL,
                    'icon': 'fa-bug',
                    'label': 'Bug reports'
                }
            ],
            'legal': [
                {
                    'url': bca_url('legal'),
                    'icon': 'fa-shield-halved',
                    'label': 'Legal Notice & Privacy Policy'
                }, {
                    'url': bca_url('cookies'),
                    'icon': 'fa-cookie-bite',
                    'label': 'Cookies policy'
                }
            ],
            'licenses': [
                {
                    'url': 'https://fontawesome.com/license/free',
                    'icon': 'fa-brands fa-font-awesome',
                    'label': 'Icons by Font Awesome'
                },
                {
                    'url': 'https://fonts.google.com/specimen/Rubik/license',
                    'icon': 'fa-book',
                    'label': 'Rubik font by Google Fonts'
                }
            ]
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
            context['query'] = query
        return context
