from django.http import Http404
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.db.models import Case, When, OuterRef, Subquery, IntegerField, FloatField, F, Max
from django.db.models.functions import Cast

from web_app.models import Species

import json
import random

# Prepare dict of species for all views
species_dict = {}
for species in Species.objects.all():
    phylum = species.meta_set.filter(key="phylum").values_list('value', flat=True)[0]
    if phylum not in species_dict:
        species_dict[phylum] = [species]
    else:
        species_dict[phylum].append(species)


def querysetToJSON(qs):
    ''' Convert Django queryset to JSON.'''
    return json.dumps(list(qs))


def prepareHeatmapData(species):
    top_genes = 5
    minFC = 2
    scale_expression_fc = max(minFC, 6)
    
    # Get list of top genes per metacell
    genes = []
    metacells = species.metacell_set.all()
    for m in metacells:
       vals = (
           m.metacellgeneexpression_set
               .exclude(value__lt=minFC) # ignore values < minFC
               .order_by('-value')[:top_genes]
       )
       genes = genes + list(vals.values_list('gene__name', flat=True))

    # Get list of unique top genes
    genes = list(set(genes))

    # Filter data based on top genes and exclude values < minFC
    filtered = (
        species.metacellgeneexpression_set
            .filter(gene__name__in=genes)   # Only show top genes
            .exclude(value__lt=minFC)       # Exclude values < minFC
    )
    
    # Re-order genes based on highest gene expression per metacell:
    # 1. Create subquery to retrieve metacell associated with max value per gene
    # 2. Create a list with ordered genes
    
    max_value_metacell = Cast(
        Subquery(
            filtered.filter(gene=OuterRef('gene')).order_by('-value')
                    .values('metacell__name')[:1]),
        IntegerField()
    )

    ordered_genes = (
        filtered
            .values('gene')
            .annotate(
                # Annotate the max value and the corresponding metacell per gene
                max_value=Max('value'),
                metacell=max_value_metacell
            )
            .order_by('-metacell')
            .values_list('gene', flat=True)
    )

    # Order filtered queryset to match that of the ordered genes
    ordered_qs = filtered.order_by(Case(
        *[When(gene=gene, then=pos) for pos, gene in enumerate(ordered_genes)]
    ))

    # Clip max values to scale_expression_fc
    clipped = ordered_qs.annotate(
        expression=Case(
            When(value__gt=scale_expression_fc, then=scale_expression_fc),
            default=F('value'),
            output_field=FloatField(),
        )
    )

    res = querysetToJSON(clipped.values(
        'id', 'expression', 'gene__name', 'gene__description', 'gene__domains',
        'metacell__name', 'metacell__type', 'metacell__color'))
    return res, len(genes), len(metacells)


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
        context["species_dict"] = species_dict
        return context


class AtlasInfoView(TemplateView):
    model = Species
    template_name = "web_app/atlas-info.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["species"] = context["species"].replace("_", " ")
        try:
            context["species"] = Species.objects.filter(scientific_name=context["species"])[0]
            context["species_dict"] = species_dict
        except:
            raise Http404(str(context["species"]) + " not found")
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
            raise Http404(str(context["species"]) + " not found")
        context["species_dict"] = species_dict

        context["sc_data"] = querysetToJSON(species.singlecell_set.values(
            "id", "x", "y", "metacell__type", "metacell__color"))

        context["mc_data"] = querysetToJSON(species.metacell_set.values(
            "id", "x", "y", "type", "color"))

        context["mc_links"] = querysetToJSON(species.metacelllink_set.values(
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
            context["species_dict"] = species_dict
        except:
            raise Http404(str(context["species"]) + " not found")
        return context


class ComparisonView(TemplateView):
    template_name = "web_app/comparison.html"


class DownloadsView(TemplateView):
    template_name = "web_app/downloads.html"


class BlogView(TemplateView):
    template_name = "web_app/blog.html"


class AboutView(TemplateView):
    template_name = "web_app/about.html"
