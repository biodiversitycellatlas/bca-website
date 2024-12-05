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


def prepareHeatmapData(species, n_top_genes=5, minFC=2):    
    ''' Prepare data for heatmap '''
    scale_expression_fc = max(minFC, 6)

    # Get list of top genes per metacell
    top_genes = list(
        species.metacellgeneexpression_set
            .filter(fold_change__gte=minFC)
            .annotate(rank=Window(expression=Rank(),
                                  partition_by='metacell_id',
                                  order_by=F('fold_change').desc()))
            .filter(rank__lte=n_top_genes)
            .values_list("gene__name", flat=True))
    top_genes = list(set(top_genes))

    # Filter data based on top genes and exclude FC < minFC
    filtered = species.metacellgeneexpression_set.filter(
        gene__name__in=top_genes, fold_change__gte=minFC)
    
    # Re-order genes based on highest gene expression per metacell
    ordered_genes = filtered.annotate(
        rank=Window(
            expression=Rank(),
            partition_by='gene__name',
            order_by=F('fold_change').desc()
        )
    ).filter(rank=1).order_by(
        -Cast('metacell__name', IntegerField())
    ).values_list("gene", flat=True)

    # Order filtered queryset to match that of the ordered genes
    ordered_qs = filtered.order_by(Case(
        *[When(gene=gene, then=pos) for pos, gene in enumerate(ordered_genes)]
    ))

    # Log2-transform values and clip maximum value to scale_expression_fc
    clipped = ordered_qs.annotate(
        fold_change_log2=Log(2, 'fold_change'),
        log2_expression=Case(
            When(fold_change_log2__gt=scale_expression_fc, then=scale_expression_fc),
            default=F('fold_change_log2'),
            output_field=FloatField(),
        )
    )

    res = convertQuerysetToJSON(clipped.values(
        'id', 'log2_expression', 'gene__name', 'gene__description', 'gene__domains',
        'metacell__name', 'metacell__type', 'metacell__color'))
    return res, len(top_genes), species.metacell_set.count()


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

        context["sc_data"] = convertQuerysetToJSON(species.singlecell_set.values(
            "name", "x", "y", "metacell__type", "metacell__color"))

        context["mc_data"] = convertQuerysetToJSON(species.metacell_set.values(
            "name", "x", "y", "type", "color"))

        context["mc_links"] = convertQuerysetToJSON(species.metacelllink_set.values(
            "metacell__x", "metacell__y", "metacell2__x", "metacell2__y"))

        # Get URL query parameters and prepare table with cell markers
        query = self.request.GET
        context['query'] = query
        markers = int(query.get('markers', 5))
        fc_min = float(query.get('fc_min', 2))

        (expr, expr_genes, expr_metacells) = prepareHeatmapData(species, markers, fc_min)
        context["expr"] = expr
        context["expr_genes"] = expr_genes
        context["expr_metacells"] = expr_metacells
        return context


class AtlasGeneView(BaseAtlasView):
    template_name = "web_app/atlas_gene.html"


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
