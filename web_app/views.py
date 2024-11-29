from django.http import Http404
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.db.models import Case, When, OuterRef, Subquery, IntegerField, FloatField, F, Max, Window
from django.db.models.functions import Cast, Rank, Log

from web_app.models import Species

import json
import random

# Prepare dict of species for all views
def getSpeciesDict():
    species_dict = {}
    for species in Species.objects.all():
        # get phylum
        try:
            phylum = species.meta_set.filter(key="phylum").values_list('value', flat=True)[0]
        except:
            phylum = "Other phyla"

        # get meta info
        try:
            removed_terms = ['species','taxon_id', 'phylum']
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


def convertQuerysetToJSON(qs):
    ''' Convert Django queryset to JSON.'''
    return json.dumps(list(qs))


def prepareHeatmapData(species, n_top_genes=5, minFC=2):    
    scale_expression_fc = max(minFC, 6)

    # Get list of top genes per metacell
    top_genes = list(
        species.metacellgeneexpression_set
            .exclude(value__lt=minFC)
            .annotate(rank=Window(expression=Rank(),
                                  partition_by='metacell_id',
                                  order_by=F('value').desc()))
            .filter(rank__lte=5)
            .values_list("gene__name", flat=True)
    )
    top_genes = list(set(top_genes))

    # Filter data based on top genes and exclude values < minFC
    filtered = (
        species.metacellgeneexpression_set
            .filter(gene__name__in=top_genes)
            .exclude(value__lt=minFC)
    )
    
    # Re-order genes based on highest gene expression per metacell
    ordered_genes = (
        filtered
            .annotate(rank=Window(expression=Rank(),
                partition_by='gene__name',
                order_by=F('value').desc()))
            .filter(rank=1)
            .order_by(-Cast('metacell__name', IntegerField()))
            .values_list("gene", flat=True)
    )

    # Order filtered queryset to match that of the ordered genes
    ordered_qs = filtered.order_by(Case(
        *[When(gene=gene, then=pos) for pos, gene in enumerate(ordered_genes)]
    ))

    # Log2-transform values and clip maximum value to scale_expression_fc
    clipped = ordered_qs.annotate(
        value_log2=Log(2, 'value'),
        log2_expression=Case(
            When(value_log2__gt=scale_expression_fc, then=scale_expression_fc),
            default=F('value_log2'),
            output_field=FloatField(),
        )
    )

    res = convertQuerysetToJSON(clipped.values(
        'id', 'log2_expression', 'gene__name', 'gene__description', 'gene__domains',
        'metacell__name', 'metacell__type', 'metacell__color'))
    return res, len(top_genes), species.metacell_set.count()


class IndexView(TemplateView):
    template_name = "web_app/index.html"


class AtlasView(TemplateView):
    template_name = "web_app/atlas.html"

    def get(self, request, *args, **kwargs):
        previous_species = request.COOKIES.get('species')
        if previous_species:
            return redirect('atlas-info', previous_species)
        else:
            return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        context["icon"] = random.choice(
            ["frog", "mosquito", "cow", "otter", "kiwi-bird", "shrimp", "crow",
            "dove", "fish-fins", "cat", "locust", "tree"])
        context["species_dict"] = getSpeciesDict()
        return context


class AtlasInfoView(TemplateView):
    model = Species
    template_name = "web_app/atlas-info.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["species"] = context["species"].replace("_", " ")
        try:
            context["species"] = Species.objects.filter(scientific_name=context["species"])[0]
            context["species_dict"] = getSpeciesDict()
        except:
            raise Http404(f"Species {context['species']} not found")
        return context


class AtlasOverviewView(TemplateView):
    model = Species
    template_name = "web_app/atlas-overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["species"] = context["species"].replace("_", " ")
        try:
            species = Species.objects.filter(scientific_name=context["species"])[0]
            context["species"] = species
        except:
            raise Http404(f"Species {context['species']} not found")
        context["species_dict"] = getSpeciesDict()

        context["sc_data"] = convertQuerysetToJSON(species.singlecell_set.values(
            "id", "x", "y", "metacell__type", "metacell__color"))

        context["mc_data"] = convertQuerysetToJSON(species.metacell_set.values(
            "id", "x", "y", "type", "color"))

        context["mc_links"] = convertQuerysetToJSON(species.metacelllink_set.values(
            "metacell__x", "metacell__y", "metacell2__x", "metacell2__y"))

        (expr, expr_genes, expr_metacells) = prepareHeatmapData(species)
        context["expr"] = expr
        context["expr_genes"] = expr_genes
        context["expr_metacells"] = expr_metacells
        return context


class AtlasMarkersView(TemplateView):
    model = Species
    template_name = "web_app/atlas-markers.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["species"] = context["species"].replace("_", " ")
        try:
            context["species"] = Species.objects.filter(scientific_name=context["species"])[0]
            context["species_dict"] = getSpeciesDict()
        except:
            raise Http404(f"Species {context['species']} not found")

        # Get URL query parameters
        context['query'] = self.request.GET

        # Calculate markers
        return context


class ComparisonView(TemplateView):
    template_name = "web_app/comparison.html"


class DownloadsView(TemplateView):
    template_name = "web_app/downloads.html"


class BlogView(TemplateView):
    template_name = "web_app/blog.html"


class AboutView(TemplateView):
    template_name = "web_app/about.html"
