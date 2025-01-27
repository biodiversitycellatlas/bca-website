from django.http import Http404
from django.shortcuts import redirect, reverse
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView

from django.db.models import Q

from .models import Species

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
    template_name = "app/index.html"


class AtlasView(TemplateView):
    template_name = "app/atlas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["icon"] = random.choice(
            ["frog", "mosquito", "cow", "otter", "kiwi-bird", "shrimp", "crow",
            "dove", "fish-fins", "cat", "locust", "tree", "spider", "hippo"])
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
    template_name = "app/atlas_info.html"

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
    template_name = "app/atlas_info.html"


class AtlasOverviewView(BaseAtlasView):
    template_name = "app/atlas_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        species = context['species']
        if not isinstance(species, Species):
            return context

        context['metacell_dict'] = getMetacellDict(species)

        # Get URL query parameters
        query = self.request.GET
        context['query'] = query
        return context


class AtlasGeneView(BaseAtlasView):
    template_name = "app/atlas_gene.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        species = context.get('species')
        if not isinstance(species, Species):
            return context

        gene = context.get('gene')
        if gene:
            # Fetch information on selected gene
            obj = species.gene_set.filter(name=gene)
            if obj:
                context['gene'] = obj.first()
            else:
                # Throw a warning if gene does not exist
                context['gene'] = ''
                context['warning'] = {
                    'title': f'Invalid gene <code>{gene}</code>!',
                    'description': f"Please check available genes in the search box above."
                }

        query = self.request.GET
        context['query'] = query
        return context


class AtlasMarkersView(BaseAtlasView):
    template_name = "app/atlas_markers.html"

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
                # get selected metacells
                metacells = query['metacells'].split(',')
                selected = list(species.metacell_set.filter(
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
    template_name = "app/atlas_compare.html"


class ComparisonView(TemplateView):
    template_name = "app/comparison.html"


class DownloadsView(TemplateView):
    template_name = "app/downloads.html"


class BlogView(TemplateView):
    template_name = "app/blog.html"


class AboutView(TemplateView):
    template_name = "app/about.html"
