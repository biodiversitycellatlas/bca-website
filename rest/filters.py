from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    ChoiceFilter,
    FilterSet,
    ModelChoiceFilter,
    NumberFilter,
    NumericRangeFilter,
    OrderingFilter,
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

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema_field

from app import models
from .functions import ArrayToString, ArrayPosition
from .aggregates import Median
from .utils import check_model_exists

def skip_param(queryset, name, value):
    '''
    Function to allow to document a parameter without actually running anything.
    Useful if the param is used elsewhere.
    '''
    return queryset


class SpeciesChoiceFilter(ChoiceFilter):
    default_field_name = 'species'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('field_name', self.default_field_name)
        kwargs.setdefault(
            'label',
            "The <a href='#/operations/species_list'>species' scientific name</a>.")

        choices = [
            (s.scientific_name, s.common_name)
            for s in models.Species.objects.all()
        ] if check_model_exists(models.Species) else []
        kwargs['choices'] = choices
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        # Optimise query: filter by species_id directly to avoid inner joins
        if value:
            # Build species_id field based on given field_name
            species_id_field = 'species_id'
            if self.field_name != 'species':
                species_id_field = f'{self.field_name}__{species_id_field}'

            # Filter by ID directly
            species_subquery = models.Species.objects.filter(
                scientific_name=value
            ).values('id')[:1]
            qs = qs.filter(**{species_id_field: Subquery(species_subquery)})
        else:
            qs = super().filter(qs, value)
        return qs


class QueryFilterSet(FilterSet):
    '''
    Base class to add a query parameter to search through multiple fields
    from a model.
    '''

    # Array of strings to use when querying
    query_fields = []
    threshold = 0.3

    def query(self, queryset, name, value):
        if value:
            expr = []
            for field in self.query_fields:
                # Aggregate to avoid multiple results from query lookups (e.g., meta__value)
                results = Max(TrigramStrictWordSimilarity(value, field))
                expr.append(results)

            # Use the greatest value if multiple exist
            similarity = Greatest(*expr) if len(expr) > 1 else expr[0]

            # Filter results based on a given threshold
            queryset = queryset.annotate(similarity=similarity).filter(similarity__gt=self.threshold)

            # If unsorted, sort results by similarity
            if not queryset.query.order_by:
                queryset = queryset.order_by('-similarity')
        return queryset


class SpeciesFilter(QueryFilterSet):
    q = CharFilter(method = 'query')
    query_fields = ['common_name', 'scientific_name', 'meta__value']


class GeneFilter(QueryFilterSet):
    species = SpeciesChoiceFilter()
    genes = CharFilter(
        label = "Comma-separated list of <a href='#/operations/gene_list'>genes</a>, <a href='#/operations/gene_lists_list'>gene lists</a> and <a href='#/operations/domain_list'>domains</a> to retrieve data for. If not provided, data is returned for all genes.",
        method='filter_genes')
    q = CharFilter(
        method = 'query',
        label = "Query string to filter results. The string will be searched and ranked across gene names, descriptions, and domains."
    )
    query_fields = ['name', 'description', 'domains__name']

    def filter_genes(self, queryset, name, value):
        if value:
            genes = value.split(',')
            queryset = queryset.filter(
                Q(name__in=genes) |
                Q(domains__name__in=genes) |
                Q(genelists__name__in=genes)
            )
        return queryset

    class Meta:
        model = models.Gene
        fields = ['species']


class DomainFilter(QueryFilterSet):
    species = SpeciesChoiceFilter(field_name='gene')
    q = CharFilter(
        method = 'query',
        label = "Query string to filter results. The string will be searched and ranked across domain names."
    )
    query_fields = ['name']

    order_by_gene_count = BooleanFilter(
        method='order',
        label="Order results by gene count (ascending).")

    def order(self, queryset, name, value):
        if value:
            queryset = queryset.order_by('-gene_count')
        return queryset

    class Meta:
        model = models.Domain
        fields = ['species']

    def filter_queryset(self, queryset):
        # Avoid returning duplicate gene lists because of the species filter
        queryset = super().filter_queryset(queryset)
        return queryset.distinct()


class GeneListFilter(FilterSet):
    species = SpeciesChoiceFilter(field_name="gene")

    class Meta:
        model = models.GeneList
        fields = ['species']

    def filter_queryset(self, queryset):
        # Avoid returning duplicate gene lists because of the species filter
        queryset = super().filter_queryset(queryset)
        return queryset.distinct()


class OrthologFilter(FilterSet):
    gene = CharFilter(
        method = 'find_orthologs',
        label = "The <a href='#/operations/gene_list'>gene name</a> for ortholog search. If not defined, returns all orthologs.")
    expression = BooleanFilter(
        method = skip_param, # used in serializers.py: OrthologSerializer
        label ='Show metacell gene expression for each gene (default: <kbd>false</kbd>).')
    species = SpeciesChoiceFilter()

    class Meta:
        model = models.Ortholog
        fields = ['species']

    def find_orthologs(self, queryset, name, value):
        if value:
            orthogroup = queryset.filter(gene__name=value).values('orthogroup')[:1]
            return queryset.filter(orthogroup=orthogroup)
        return queryset


class SingleCellFilter(FilterSet):
    species = SpeciesChoiceFilter(required=True)
    gene = CharFilter(
        method=skip_param,
        label="Retrieve expression for a given <a href='#/operations/gene_list'>gene</a>.")

    class Meta:
        model = models.SingleCell
        fields = ['species']


class MetacellFilter(FilterSet):
    species = SpeciesChoiceFilter(required=True)
    gene = CharFilter(
        method=skip_param,
        label="Retrieve expression for a given <a href='#/operations/gene_list'>gene</a>.")

    class Meta:
        model = models.Metacell
        fields = ['species']


class MetacellLinkFilter(FilterSet):
    species = SpeciesChoiceFilter(required=True)

    class Meta:
        model = models.MetacellLink
        fields = ['species']


class MetacellCountFilter(FilterSet):
    species = SpeciesChoiceFilter(field_name="metacell", required=True)


class SingleCellGeneExpressionFilter(FilterSet):
    species = SpeciesChoiceFilter(required=True)
    genes = CharFilter(
        label = "Comma-separated list of <a href='#/operations/gene_list'>genes</a>, <a href='#/operations/gene_lists_list'>gene lists</a> and <a href='#/operations/domain_list'>domains</a> to retrieve data for. If not provided, data is returned for all genes.",
        method='filter_genes')

    def filter_genes(self, queryset, name, value):
        if value:
            genes = value.split(',')
            queryset = queryset.filter(
                Q(gene__name__in=genes) |
                Q(gene__domains__name__in=genes) |
                Q(gene__genelists__name__in=genes)
            )
        return queryset

    class Meta:
        model = models.SingleCellGeneExpression
        fields = ['species']


class MetacellGeneExpressionFilter(FilterSet):
    species = SpeciesChoiceFilter(required=True)
    genes = CharFilter(
        label = "Comma-separated list of <a href='#/operations/gene_list'>genes</a>, <a href='#/operations/gene_lists_list'>gene lists</a> and <a href='#/operations/domain_list'>domains</a> to retrieve data for. If not provided, data is returned for all genes.",
        method='filter_genes')
    metacells = CharFilter(
        label = "Comma-separated list of <a href='#/operations/metacell_list'>metacell names and cell types</a>.",
        method = "filter_metacells")
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

    def filter_genes(self, queryset, name, value):
        if value:
            genes = value.split(',')
            queryset = queryset.filter(
                Q(gene__name__in=genes) |
                Q(gene__domains__name__in=genes) |
                Q(gene__genelists__name__in=genes)
            )
        return queryset

    def filter_metacells(self, queryset, name, value):
        if value:
            metacells = value.split(',')
            # Filter metacells by name and type
            selected = (
                Q(metacell__name__in=metacells) |
                Q(metacell__type__name__in=metacells)
            )
            queryset = queryset.filter(selected)
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
            sorted_genes = queryset.annotate(
                rank=Window(
                    expression=Rank(),
                    partition_by='gene__name',
                    order_by=F('fold_change').desc()
                )
            ).filter(rank=1).order_by(
                -Cast('metacell__name', IntegerField())
            ).values_list('gene', flat=True)

            sorted_genes = list(sorted_genes)

            # Sort queryset based on gene list
            queryset = queryset.order_by(ArrayPosition('gene', array=sorted_genes))
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


class CorrelatedGenesFilter(QueryFilterSet):
    species = SpeciesChoiceFilter(required=True)
    gene = CharFilter(
        label = "<a href='#/operations/gene_list'>Gene symbol</a> to retrieve top correlated genes for.",
        method='filter_gene', required=True
    )
    ordering = OrderingFilter(
        label = "Comma-separated list of attributes to order results.",
        fields=(
            ('spearman_rho', 'spearman_rho'),
            ('spearman_pvalue', 'spearman_pvalue'),
            ('pearson_r', 'pearson_r'),
            ('pearson_pvalue', 'pearson_pvalue'),
        ),
        field_labels={
            'spearman_rho': 'Spearman rho',
            'spearman_pvalue': 'Spearman p-value',
            'pearson_r': 'Pearson r',
            'pearson_pvalue': 'Pearson p-value',
        }
    )
    q = CharFilter(
        method = 'query',
        label = "Query string to filter results. The string will be searched and ranked across gene names, descriptions, and domains."
    )
    query_fields = [
        'gene__name', 'gene__description', 'gene__domains__name',
        'gene2__name', 'gene2__description', 'gene2__domains__name',
    ]

    def filter_gene(self, queryset, name, value):
        if value:
            id = models.Gene.objects.filter(name=value).values_list('id')[0][0]
            queryset = queryset.filter( Q(gene=id) | Q(gene2=id) )
        return queryset

    class Meta:
        model = models.GeneCorrelation
        fields = ['species', 'gene']


def createFCtypeChoiceFilter(mode, ignoreMode=False):
    if mode == 'minimum':
        var = 'fc_min'
        sign = '≥'
        target = 'foreground (i.e., selected) metacells'
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
    species = SpeciesChoiceFilter(required=True)
    metacells = CharFilter(
        label = "Comma-separated list of <a href='#/operations/metacell_list'>metacell names and cell types</a>.",
        method = "select_metacells",
        required = True)

    fc_min = NumberFilter(
        label = "Filter genes across foreground (i.e., selected) metacells by their minimum fold-change (default: <kbd>2</kbd>).",
        method = skip_param)
    fc_min_type = createFCtypeChoiceFilter('minimum')

    fc_max_bg = NumberFilter(
        label = "Filter genes across background (i.e., non-selected) metacells by their maximum fold-change (default: <kbd>3</kbd>).",
        method = skip_param)
    fc_max_bg_type = createFCtypeChoiceFilter('maximum', ignoreMode=True)

    def select_metacells(self, queryset, name, value):
        # Select foreground (selected) and background metacells
        metacells = value.split(',')
        fg_metacells = (
            # Check by metacell name
            Q(metacellgeneexpression__metacell__name__in=metacells) |
            # Check by metacell type
            Q(metacellgeneexpression__metacell__type__name__in=metacells)
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
            fg_mean_fc=Avg(mge_fc, filter=fg_metacells),
            bg_mean_fc=Avg(mge_fc, filter=bg_metacells),
            bg_median_fc=Median(mge_fc, filter=bg_metacells)
        )
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
        fc_max_bg = self.data.get('fc_min', 3)
        # Discard "gap genes" based on background
        if not value or value == 'ignore':
            # Ignore backgound filtering
            return queryset
        elif value == 'mean':
            # Keep genes whose mean FC across background <= fc_max_bg
            queryset = queryset.filter(bg_mean_fc__lte=fc_max_bg)
        elif value == 'median':
            # Keep genes whose median FC across background <= fc_max_bg
            queryset = queryset.filter(bg_median_fc__lte=fc_max_bg)
        return queryset

    class Meta:
        model = models.Gene
        fields = ['species']
