from django_filters.rest_framework import FilterSet, ModelChoiceFilter, CharFilter
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.functions import Greatest
from django.contrib.postgres.search import TrigramStrictWordSimilarity

from web_app import models
from .functions import ArrayToString

def getSpeciesChoiceFilter():
    return ModelChoiceFilter(
        queryset = models.Species.objects.all(),
        field_name = "species__scientific_name",
        to_field_name = "scientific_name",
        label = "Species scientific name (example: <i>Trichoplax adhaerens</i>).",
        required = True
    )


class GeneFilter(FilterSet):
    species = getSpeciesChoiceFilter()
    q = CharFilter(
        method = 'query',
        label = "Query string to filter results (example: <kbd>ATP binding</kbd>). The string will be searched and ranked across gene names, descriptions, and domains."
    )

    class Meta:
        model = models.Gene
        fields = ['species']

    def query(self, queryset, name, value):
        if value:
            return queryset.annotate(
                        similarity=Greatest(
                            TrigramStrictWordSimilarity(value, 'name'),
                            TrigramStrictWordSimilarity(value, 'description'),
                            TrigramStrictWordSimilarity(value, ArrayToString('domains'))
                        )
                    ).filter(similarity__gt=0.3).order_by('-similarity')
        return queryset


class MetacellFilter(FilterSet):
    species = getSpeciesChoiceFilter()

    class Meta:
        model = models.Metacell
        fields = ['species']


class MetacellGeneExpressionFilter(FilterSet):
    species = getSpeciesChoiceFilter()

    class Meta:
        model = models.MetacellGeneExpression
        fields = ['species']
