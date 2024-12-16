from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    ChoiceFilter,
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
from .aggregates import Median

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
    genes = CharFilter(
        label = 'Comma-separated list of genes to retrieve data for. If not provided, data is returned for all genes.',
        method='filter_genes_in')
    fc_min = NumberFilter(
        label = 'Filter expression data by minimum fold-change (default: <kbd>0</kbd>).',
        field_name = 'fold_change', lookup_expr='gte')
    n_markers = NumberFilter(
        label = 'Filter data based on a number of the top genes of each metacell (markers).',
        method = 'filter_markers')
    sort_genes = BooleanFilter(
        label = 'Sort genes based on their highest gene expression across metacells (default: <kbd>false</kbd>).',
        method = 'sort_genes_across_metacells')
    log2 = BooleanFilter(
        label = 'Log2-transform <kbd>fold_change</kbd> (default: <kbd>false</kbd>).',
        method = 'log2_transform')
    clip_log2 = NumberFilter(
        label='Set the maximum limit for <kbd>log2_fold_change</kbd> values (requires <kbd>log2=true</kbd>). If <kbd>fc_min</kbd> is higher, <kbd>clip_log2</kbd> is set to <kbd>fc_min</kbd>.',
        method='clip_expression')

    def filter_genes_in(self, queryset, name, value):
        if value:
            queryset = queryset.filter(gene__name__in=value.split(','))
        return queryset

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


def createFCtypeChoiceFilter(mode, ignoreMode=False):
    if mode == 'minimum':
        var = 'fc_min'
        sign = '≥'
        target = 'selected metacells'
        default = 'min'
        method = 'filter_fc_min'
        required = True
    else:
        var = 'bg_fc_max'
        sign = '≤'
        target = 'background (i.e., non-selected) metacells'
        default = 'ignore'
        method = 'filter_fc_max_bg'
        required = False

    choices = [[item, f'Keep genes whose {item} fold-change across {target} {sign} <kbd>{var}</kbd>'] for item in ['mean', 'average']]

    if ignoreMode:
        choices.append(['ignore', 'Skip this filtering'])

    res = ChoiceFilter(
        choices = choices,
        label = f"Type of filtering to use for the {mode} fold-change threshold (default: <kbd>{default}</kbd>).",
        method = method,
        required = required
    )
    return res


class MetacellMarkerFilter(FilterSet):
    species = getSpeciesChoiceFilter()
    metacells = CharFilter(
        label = "Comma-separated list of metacell names and cell types (example: <i>12,30,Peptidergic1</i>).",
        method = "select_metacells",
        required=True)

    fc_min = NumberFilter(
        label = "Filter genes across metacells by their minimum fold-change (default: <kbd>2</kbd>).",
        method = "skip_filter")
    fc_min_type = createFCtypeChoiceFilter('minimum')

    fc_max_bg = NumberFilter(
        label = "Filter genes across background (i.e., non-selected) metacells by their maximum fold-change (default: <kbd>6</kbd>).",
        method = "skip_filter")
    fc_max_bg_type = createFCtypeChoiceFilter('maximum', ignoreMode=True)

    def select_metacells(self, queryset, name, value):
        # Select foreground (selected) and background metacells
        metacells = value.split(',')
        fg_metacells = (
            # Check by metacell name
            Q(metacellgeneexpression__metacell__name__in=metacells) |
            # Check by metacell type
            Q(metacellgeneexpression__metacell__type__in=metacells)
        )
        bg_metacells = ~fg_metacells

        # Calculate gene's UMI fraction
        mge_umi = "metacellgeneexpression__umi_raw"
        queryset = queryset.annotate(
            bg_sum_umi=Sum(mge_umi, filter=bg_metacells),
            fg_sum_umi=Sum(mge_umi, filter=fg_metacells)
        ).annotate(
            umi_perc=F('fg_sum_umi') / (F('fg_sum_umi') + F('bg_sum_umi')) * 100)
    
        # Calculate median FC per gene
        mge_fc = "metacellgeneexpression__fold_change"
        queryset = queryset.annotate(
            fg_median_fc=Median(mge_fc, filter=fg_metacells),
            fg_mean_fc=Avg(mge_fc, filter=fg_metacells))
        return queryset

    def filter_fc_min(self, queryset, name, value):
       # Get "gap genes" (those specifically expressed in selected metacells)
        fc_min = self.data.get('fc_min', 2)

        if not value or value == 'mean':
            # Keep genes whose mean FC across selected metacells >= fc_min
            queryset = queryset.filter(fg_mean_fc__gte=fc_min)
        elif value == 'median':
            # Keep genes whose median FC across selected metacells >= fc_min
            queryset = queryset.filter(fg_median_fc__gte=fc_min)
        return queryset

    def filter_fc_max_bg(self, queryset, name, value):
        fc_min = self.data.get('fc_min', 2)
        # Discard "gap genes" based on background
        if not value or value == 'ignore':
            # Ignore backgound filtering
            return queryset
        elif value == 'mean':
            # Keep genes whose mean FC across background <= fc_max_bg
            queryset = queryset.annotate(
                bg_avg_fc=Avg(mge_fc, filter=bg_metacells)
            ).filter(bg_avg_fc__lte=query['fc_max_bg'])
        elif value == 'median':
            # Keep genes whose median FC across background <= fc_max_bg
            queryset = queryset.annotate(
                bg_median_fc=Median(mge_fc, filter=bg_metacells)
            ).filter(bg_median_fc__lte=query['fc_max_bg'])
        return queryset

    def skip_filter(self, queryset, name, value):
        # These params are already consumed by other functions
        return queryset

    class Meta:
        model = models.Gene
        fields = ['species']
