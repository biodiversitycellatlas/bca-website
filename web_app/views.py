from django.http import Http404
from django.shortcuts import redirect, reverse
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.db.models import (
    Avg,
    Case,
    F,
    FloatField,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
    Sum,
    When,
    Window
)
from django.db.models.functions import Cast, Rank, Log

from web_app.models import Species
from web_app.aggregates import Median

import json
import random


def getSpeciesDict():
    ''' Prepare dictionary of species. '''
    species_dict = {}
    for species in Species.objects.all():
        # get phylum
        try:
            phylum = species.meta_set.filter(key="phylum").values_list('value', flat=True)[0]
        except:
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ['species', 'phylum']
            meta = list(species.meta_set.exclude(key__in=removed_terms)
                                        .values_list('value', flat=True))
        except:
            meta = list()

        elem = {'species': species, 'meta': meta}
        if phylum not in species_dict:
            species_dict[phylum] = [elem]
        else:
            species_dict[phylum].append(elem)
    return species_dict


def getMetacellDict(species):
    ''' Prepare dictionary of metacells for a species. '''
    metacells = species.metacell_set.all()

    # Group by cell type
    types = dict()
    for obj in metacells:
        types.setdefault(obj.type, []).append(obj)

    # Return metacells by cell types and all together
    metacell_dict = {'Cell types': types, 'Metacells': list(metacells)}
    return metacell_dict


def convertQuerysetToJSON(qs):
    ''' Convert Django queryset to JSON. '''
    return json.dumps(list(qs))


def getMarkersTable(species, query):
    ''' Prepare table with cell markers based on query. '''

    # Select foreground (selected) and background metacells:
    metacells = query['metacells'].split(',')
    selected = list(species.metacell_set.filter(
        Q(name__in=metacells) | Q(type__in=metacells)).values_list('name', flat=True).distinct())
    selected = [int(s) for s in selected]
    selected.sort()

    fg_metacells = (
        # Check by metacell name
        Q(metacellgeneexpression__metacell__name__in=metacells) |
        # Check by metacell type
        Q(metacellgeneexpression__metacell__type__in=metacells)
    )
    bg_metacells = ~fg_metacells

    # Calculate gene's UMI fraction
    mge_umi = "metacellgeneexpression__umi_raw"
    data = species.gene_set.annotate(
        fg_sum_umi=Sum(mge_umi, filter=fg_metacells),
        bg_sum_umi=Sum(mge_umi, filter=bg_metacells)
    ).annotate(
        umi_perc=F('fg_sum_umi') / (F('fg_sum_umi') + F('bg_sum_umi')) * 100)

    # Calculate median FC per gene
    mge_fc = "metacellgeneexpression__fold_change"
    data = data.annotate(
        fg_median_fc=Median(mge_fc, filter=fg_metacells),
        fg_mean_fc=Avg(mge_fc, filter=fg_metacells))

    # Get "gap genes" (those specifically expressed in selected metacells)
    fc_min_type = query['fc_min_type'] if 'fc_min_type' in query.keys() else 'mean'
    fc_min = query['fc_min'] if 'fc_min' in query.keys() else 2

    if fc_min_type == 'mean':
        # Keep genes whose FC across all selected metacells >= fc_min
        data = data.filter(fg_mean_fc__gte=fc_min)
    elif fc_min_type == 'median':
        # Keep genes whose median FC across selected metacells >= fc_min
        data = data.filter(fg_median_fc__gte=fc_min)

    fc_max_bg_type = query['fc_max_bg_type'] if 'fc_max_bg_type' in query.keys() else 'ignore'
    # Discard "gap genes" based on background
    if fc_max_bg_type == 'ignore':
        # Ignore backgound filtering
        data = data
    elif fc_max_bg_type == 'mean':
        # Keep genes whose FC across all background <= fc_max_bg
        data = data.annotate(
            bg_avg_fc=Avg(mge_fc, filter=bg_metacells)
        ).filter(bg_avg_fc__lte=query['fc_max_bg'])
    elif fc_max_bg_type == 'median':
        # Keep genes whose median FC across background <= fc_max_bg
        data = data.annotate(
            bg_median_fc=Median(mge_fc, filter=bg_metacells)
        ).filter(bg_median_fc__lte=query['fc_max_bg'])

    table = convertQuerysetToJSON(data.values(
        'id', 'name', 'description', 'domains',
        'fg_sum_umi', 'umi_perc', 'fg_mean_fc', 'fg_median_fc'))
    return table, selected


def getSpecies(species):
    ''' Returns species if it exists in the database; returns None otherwise. '''
    if isinstance(species, Species):
        return obj
    
    species = species.replace("_", " ")
    try:
        obj = Species.objects.filter(scientific_name=species)[0]
    except:
        obj = None
    return obj


class IndexView(TemplateView):
    template_name = "web_app/index.html"


class AtlasView(TemplateView):
    template_name = "web_app/atlas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["icon"] = random.choice(
            ["frog", "mosquito", "cow", "otter", "kiwi-bird", "shrimp", "crow",
            "dove", "fish-fins", "cat", "locust", "tree"])
        context["species_dict"] = getSpeciesDict()

        query = self.request.GET
        if query and query.get('species'):
            species = getSpecies(query['species'])
            if isinstance(species, Species):
                context['species'] = species
            else:
                # Warn that species is not available in the database
                context['warning'] = {
                    'title': f'Invalid species <code>{query['species']}</code>!',
                    'description': f"Please check available species in the search box above."
                }

        return context

    def get(self, request, *args, **kwargs):
        query = self.request.GET
        species = request.COOKIES.get('species') or query.get('species')

        if species and isinstance(getSpecies(species), Species):
            return redirect('atlas_info', species)
        else:
            return super().get(request, *args, **kwargs)


class BaseAtlasView(TemplateView):
    '''
    Base view for species-specific Cell Atlas pages.
    
    Redirects to standard Atlas view with a warning when passing a species not
    available in the database.
    '''
    model = Species
    template_name = "web_app/atlas_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        species = context["species"].replace("_", " ")
        try:
            context["species"] = Species.objects.filter(scientific_name=species)[0]
        except:
            context["species"] = species
            return context

        context["species_dict"] = getSpeciesDict()
        return context

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if not isinstance(context["species"], Species):
            return redirect(reverse('atlas') + '?species=' + context["species"])
        return super().get(*args, **kwargs)


class AtlasInfoView(BaseAtlasView):
    template_name = "web_app/atlas_info.html"


class AtlasOverviewView(BaseAtlasView):
    template_name = "web_app/atlas_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        species = context['species']
        if not isinstance(species, Species):
            return context

        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        context['query'] = query
        markers = int(query.get('markers', 5))
        fc_min = float(query.get('fc_min', 2))
        return context


class AtlasGeneView(BaseAtlasView):
    template_name = "web_app/atlas_gene.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        species = context["species"]
        if not isinstance(species, Species):
            return context

        query = self.request.GET
        if query:
            context['query'] = query
        return context


class AtlasMarkersView(BaseAtlasView):
    template_name = "web_app/atlas_markers.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        species = context["species"]
        if not isinstance(species, Species):
            return context

        context['metacell_dict'] = getMetacellDict(species)

        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        if query:
            context['query'] = query
            if 'metacells' in query.keys():
                table, selected = getMarkersTable(context["species"], query)
                context['markers_table'] = table
                context['selected_metacells'] = selected
            else:
                context['warning'] = {
                    'title': 'Invalid URL!',
                    'description': f"There is no <code>metacells</code> parameter in your query: <code>{query.urlencode()}</code>"
                }
        return context


class AtlasCompareView(BaseAtlasView):
    template_name = "web_app/atlas_compare.html"


class ComparisonView(TemplateView):
    template_name = "web_app/comparison.html"


class DownloadsView(TemplateView):
    template_name = "web_app/downloads.html"


class BlogView(TemplateView):
    template_name = "web_app/blog.html"


class AboutView(TemplateView):
    template_name = "web_app/about.html"
