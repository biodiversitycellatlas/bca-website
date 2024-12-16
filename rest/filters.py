from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    ModelChoiceFilter,
    NumberFilter,
    NumericRangeFilter,
)
from django.core.exceptions import ValidationError
from django.contrib.postgres.search import TrigramStrictWordSimilarity
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
    Value,
    When,
    Window
)
from django.db.models.functions import Cast, Greatest, Log, Rank

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


class SingleCellFilter(FilterSet):
    species = getSpeciesChoiceFilter()

    class Meta:
        model = models.SingleCell
        fields = ['species']


class MetacellFilter(FilterSet):
    species = getSpeciesChoiceFilter()

    class Meta:
        model = models.Metacell
        fields = ['species']


class MetacellLinkFilter(FilterSet):
    species = getSpeciesChoiceFilter()

    class Meta:
        model = models.MetacellLink
        fields = ['species']


class MetacellGeneExpressionFilter(FilterSet):
    species = getSpeciesChoiceFilter()
    fc_min = NumberFilter(
        label = 'Filter expression data by minimum fold-change.',
        field_name = 'fold_change', lookup_expr='gte')
    n_markers = NumberFilter(
        label = 'Filter data based on a number of the top genes of each metacell (markers).',
        method = 'filter_markers')
    sort_genes = BooleanFilter(
        label = 'Sort genes based on their highest gene expression across metacells.',
        method = 'sort_genes_across_metacells')
    log2 = BooleanFilter(
        label = 'Log2-transform <kbd>fold_change</kbd> (default: <kbd>false</kbd>).',
        method = 'log2_transform')
    clip_log2 = NumberFilter(
        label='Set the maximum limit for <kbd>log2_fold_change</kbd> values (requires <kbd>log2=true</kbd>). If <kbd>fc_min</kbd> is higher, <kbd>clip_log2</kbd> is set to <kbd>fc_min</kbd>.',
        method='clip_expression')

    def filter_markers(self, queryset, name, value):
        ''' Filter data based on top genes. '''
        if value:
            top_genes = list(
                queryset
                    .annotate(rank=Window(expression=Rank(),
                                          partition_by='metacell_id',
                                          order_by=F('fold_change').desc()))
                    .filter(rank__lte=value)
                    .values_list("gene__name", flat=True))
            top_genes = list(set(top_genes)) # get unique top genes
            queryset  = queryset.filter(gene__name__in=top_genes)
        return queryset

    def sort_genes_across_metacells(self, queryset, name, value):
        ''' Sort genes by their highest gene expression across metacells. '''
        if value:
            ordered_genes = queryset.annotate(
                rank=Window(
                    expression=Rank(),
                    partition_by='gene__name',
                    order_by=F('fold_change').desc()
                )
            ).filter(rank=1).order_by(
                -Cast('metacell__name', IntegerField())
            ).values_list("gene", flat=True)
        
            # Order filtered queryset to match that of the ordered genes
            # ordered_qs = filtered.order_by(ArrayPosition('gene__name', array=ordered_genes))
            queryset = queryset.order_by(Case(
                *[When(gene=gene, then=pos) for pos, gene in enumerate(ordered_genes)]
            ))
        return queryset

    def log2_transform(self, queryset, name, value):
        ''' Log2-transform fold-change data. '''
        if value:
            queryset = queryset.annotate(log2_fold_change=Log(2, F('fold_change')))
        return queryset

    def clip_expression(self, queryset, name, value):
        ''' Limit log2-transformed fold-change data. '''
        # Check if log2 expression data is available
        log2 = self.data.get('log2', 'false') == 'true'
        if log2 and value:
            # If fc_min > value, set limit to fc_min
            fc_min = self.data.get('fc_min', 0)
            limit = max(float(fc_min), value)
            queryset = queryset.annotate(
                log2_fold_change=Case(
                    When(log2_fold_change__gt=limit, then=limit),
                    default=F('log2_fold_change'),
                    output_field=FloatField(),
                )
            )
        return queryset

    class Meta:
        model = models.MetacellGeneExpression
        fields = ['species']
