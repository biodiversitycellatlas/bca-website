from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.conf import settings
from django.db.models import F, Count, Sum, Avg, Min, Max, StdDev
from django.contrib.postgres.aggregates import ArrayAgg

from app import models
from .aggregates import PercentileCont
from .utils import check_model_exists

from operator import attrgetter

class MetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Meta
        fields = ['key', 'value']


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.File
        fields = ['title', 'file', 'checksum']


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Source
        exclude = ['id']


class DatasetSerializer(serializers.ModelSerializer):
    source = SourceSerializer()
    species = serializers.CharField(source='species.scientific_name')
    species_common_name = serializers.CharField(source='species.common_name')
    species_image_url = serializers.CharField(source='species.image_url')
    species_description = serializers.CharField(source='species.description')
    species_meta = MetaSerializer(source='species.meta_set', many=True, help_text="Metadata")
    slug = serializers.CharField()

    class Meta:
        model = models.Dataset
        fields = [
            'species', 'name', 'slug', 'description', 'image_url',
            'source', 'order', 'date_created', 'date_updated',
            'species_common_name', 'species_image_url',
            'species_description', 'species_meta'
        ]

class SpeciesSerializer(serializers.ModelSerializer):
    meta = MetaSerializer(source='meta_set', many=True, help_text="Metadata")
    files = FileSerializer(many=True, help_text="Supporting files")
    datasets = DatasetSerializer(
        many=True, help_text="Available datasets for the species")

    class Meta:
        model = models.Species
        fields = [
            'common_name', 'scientific_name', 'description', 'image_url',
            'meta', 'files', 'datasets'
        ]


class SummaryStatsSerializer(serializers.ModelSerializer):
    """ Summary statistics. """
    min = serializers.FloatField(help_text="Minimum value.")
    q1 = serializers.FloatField(help_text="First quartile (Q1) value.")
    avg = serializers.FloatField(help_text="Average value.")
    median = serializers.FloatField(help_text="Median value.")
    q3 = serializers.FloatField(help_text="Third quartile (Q3) value.")
    max = serializers.FloatField(help_text="Maximum value.")
    stddev = serializers.FloatField(help_text="Standard deviation.")

    class Meta:
        model = models.Species
        fields = ['min', 'q1', 'avg', 'median', 'q3', 'max', 'stddev']


class StatsSerializer(serializers.ModelSerializer):
    cells = serializers.SerializerMethodField(help_text="Number of cells.")
    metacells = serializers.SerializerMethodField(help_text="Number of metacells.")
    umis = serializers.SerializerMethodField(help_text="Number of unique molecular identifiers (UMIs).")
    genes = serializers.SerializerMethodField(help_text="Number of genes.")

    umis_per_metacell = serializers.SerializerMethodField()
    cells_per_metacell = serializers.SerializerMethodField()

    class Meta:
        model = models.Dataset
        fields = [
            'species', 'name', 'genes', 'cells', 'metacells',
            'umis', 'umis_per_metacell', 'cells_per_metacell'
        ]

    def get_metacell_counts(self, obj):
        return models.MetacellCount.objects.filter(metacell__dataset=obj.id)

    def get_cells(self, obj) -> int:
        return models.SingleCell.objects.filter(dataset=obj.id).count()

    def get_metacells(self, obj) -> int:
        return self.get_metacell_counts(obj).count()

    def get_umis(self, obj) -> int:
        res = self.get_metacell_counts(obj).aggregate(Sum('umis')).values()
        return list(res)[0]

    def get_genes(self, obj) -> int:
        return models.Gene.objects.filter(species__datasets=obj.id).count()

    def calculate_stats(self, obj, field):
        counts = self.get_metacell_counts(obj)

        stats = counts.aggregate(
            min=Min(field),
            q1=PercentileCont(field, percentile=0.25),
            avg=Avg(field),
            median=PercentileCont(field, percentile=0.50),
            q3=PercentileCont(field, percentile=0.75),
            max=Max(field),
            stddev=StdDev(field)
        )
        return stats

    @extend_schema_field(SummaryStatsSerializer)
    def get_cells_per_metacell(self, obj) -> int:
        return self.calculate_stats(obj, 'cells')

    @extend_schema_field(SummaryStatsSerializer)
    def get_umis_per_metacell(self, obj) -> int:
        return self.calculate_stats(obj, 'umis')


class GeneSerializer(serializers.ModelSerializer):
    species = serializers.CharField(required=False)
    genelists = serializers.StringRelatedField(many=True)
    domains = serializers.StringRelatedField(many=True)
    orthogroup = serializers.CharField()

    class Meta:
        model = models.Gene
        fields = ['species', 'name', 'description', 'domains', 'genelists', 'orthogroup']

    def __init__(self, *args, **kwargs):
        # Do not show 'species' in result if filtered in query params
        if 'context' in kwargs and 'request' in kwargs['context']:
            species = kwargs['context']['request'].GET.get('species', None)

            if species:
                self.fields.pop('species')

        super().__init__(*args, **kwargs)


class DomainSerializer(serializers.ModelSerializer):
    gene_count = serializers.IntegerField(required=False)

    class Meta:
        model = models.Domain
        fields = ['name', 'gene_count']


class GeneListSerializer(serializers.ModelSerializer):
    gene_count = serializers.SerializerMethodField(required=False)

    def get_gene_count(self, obj) -> int:
        genes = obj.gene_set
        species = self.context.get('request').query_params.get('species', None)
        if species:
            genes = genes.filter(species__scientific_name=species)
        return genes.count()

    class Meta:
        model = models.GeneList
        fields = ['name', 'description', 'gene_count']


class BaseExpressionSerializer(serializers.ModelSerializer):
    """ Base class to display gene expression for single cell and metacell serializers. """
    # Show expression data for a given gene
    expression_fields = ['gene_name', 'umi_raw', 'umifrac', 'fold_change']
    gene_name = serializers.SerializerMethodField(required=False)
    umi_raw   = serializers.SerializerMethodField(required=False)
    umifrac   = serializers.SerializerMethodField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not (request and request.query_params.get('gene')):
            for field in self.expression_fields:
                self.fields.pop(field, None)

    def get_expression_value(self, obj, field):
        """ Retrieve field from gene expression data (e.g., umi_raw). """
        gene = self.context['request'].GET.get('gene')
        if gene and obj.gene_expression:
            return attrgetter(field)(obj.gene_expression[0])
        return None

    def get_gene_name(self, obj):
        return self.context['request'].GET.get('gene')

    def get_umi_raw(self, obj):
        return self.get_expression_value(obj, 'umi_raw')

    def get_umifrac(self, obj):
        return self.get_expression_value(obj, 'umifrac')

    def get_fold_change(self, obj):
        return self.get_expression_value(obj, 'fold_change')


class SingleCellSerializer(BaseExpressionSerializer):
    # Default is null for single cells with no metacell
    metacell_name  = serializers.CharField(source='metacell.name', default=None)
    metacell_type  = serializers.CharField(source='metacell.type.name', default=None)
    metacell_color = serializers.CharField(source='metacell.type.color', default=None)

    class Meta:
        model = models.SingleCell
        exclude = ['id', 'dataset']


class MetacellSerializer(BaseExpressionSerializer):
    """ Metacell information. """
    type  = serializers.CharField(
        source='type.name', help_text="Metacell type.", required=False)
    color = serializers.CharField(
        source='type.color', help_text="Color of metacell type.", required=False)

    # Show expression for a given gene
    fold_change = serializers.SerializerMethodField(required=False)

    class Meta:
        model = models.Metacell
        exclude = ['id', 'dataset', 'links']


class MetacellLinkSerializer(serializers.ModelSerializer):
    metacell    = serializers.CharField(source='metacell.name')
    metacell_x  = serializers.FloatField(source='metacell.x')
    metacell_y  = serializers.FloatField(source='metacell.y')
    metacell2   = serializers.CharField(source='metacell2.name')
    metacell2_x = serializers.FloatField(source='metacell2.x')
    metacell2_y = serializers.FloatField(source='metacell2.y')

    class Meta:
        model = models.MetacellLink
        exclude = ['id']


class MetacellCountSerializer(serializers.ModelSerializer):
    metacell       = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type.name')
    metacell_color = serializers.CharField(source='metacell.type.color')

    cells    = serializers.IntegerField(help_text="Cell count.")
    umis     = serializers.IntegerField(help_text="UMI count.")

    class Meta:
        model = models.MetacellCount
        exclude = ['materialized_id']


class SingleCellGeneExpressionSerializer(serializers.ModelSerializer):
    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.StringRelatedField(source='gene.domains',
                                                      many=True)

    single_cell_name = serializers.CharField(source='single_cell.name')

    class Meta:
        model = models.SingleCellGeneExpression
        exclude = ['dataset']


class MetacellGeneExpressionSerializer(serializers.ModelSerializer):
    log2_fold_change = serializers.FloatField(required=False)

    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.StringRelatedField(source='gene.domains',
                                                      many=True)

    metacell_name  = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type.name')
    metacell_color = serializers.CharField(source='metacell.type.color')

    class Meta:
        model = models.MetacellGeneExpression
        exclude = ['dataset', 'id', 'gene', 'metacell']


class DatasetMetacellGeneExpressionSerializer(MetacellGeneExpressionSerializer):
    dataset = serializers.CharField(source='dataset.slug')

    gene_name        = None
    gene_description = None
    gene_domains     = None

    class Meta:
        model = MetacellGeneExpressionSerializer.Meta.model
        exclude = ['id', 'gene', 'metacell']


class CorrelatedGenesSerializer(serializers.ModelSerializer):
    name        = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    domains     = serializers.SerializerMethodField()

    class Meta:
        model = models.GeneCorrelation
        exclude = ['dataset', 'id', 'gene', 'gene2']

    def get_non_selected_gene(self, obj):
        input = self.context['request'].query_params.get('gene')
        # Return the gene that was not selected in the input
        if obj.gene.name == input:
            return obj.gene2
        else:
            return obj.gene

    def get_name(self, obj):
        gene = self.get_non_selected_gene(obj)
        return gene.name

    def get_description(self, obj):
        gene = self.get_non_selected_gene(obj)
        return gene.description

    def get_domains(self, obj):
        gene = self.get_non_selected_gene(obj)
        return [domain.name for domain in gene.domains.all()]


class MetacellMarkerSerializer(serializers.ModelSerializer):
    # Parse name of domains and gene lists
    domains = serializers.StringRelatedField(many=True)
    genelists = serializers.StringRelatedField(many=True)

    bg_sum_umi = serializers.FloatField()
    fg_sum_umi = serializers.FloatField()
    umi_perc = serializers.FloatField()
    fg_mean_fc = serializers.FloatField()
    fg_median_fc = serializers.FloatField()

    class Meta:
        model = models.Gene
        exclude = ['species', 'correlations']


class OrthologSerializer(serializers.ModelSerializer):
    species = serializers.CharField()

    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.StringRelatedField(source='gene.domains',
                                                      many=True)

    expression = DatasetMetacellGeneExpressionSerializer(
        source='gene.mge', many=True, required=False)

    class Meta:
        model = models.Ortholog
        exclude = ['id', 'gene']

    def __init__(self, *args, **kwargs):
        show_expression = kwargs['context']['request'].GET.get('expression', 'false') == 'true'
        if not show_expression:
            self.fields.pop('expression')
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Split expression by dataset
        if self.fields.get('expression'):
            all_datasets = {d.slug: d for d in models.Dataset.objects.all()}

            dataset_expr = {}
            dataset_dict = {}
            for item in data['expression']:
                dataset = item.pop('dataset')
                if dataset not in dataset_dict:
                    dataset_dict[dataset] = all_datasets[dataset]
                dataset_expr.setdefault(dataset, []).append(item)

            # Add dataset information
            data['datasets'] = DatasetSerializer(list(dataset_dict.values()), many=True).data

            ## Sort datasets by their order
            data['datasets'].sort(key=lambda x: x['order'])
            ordered_keys = [d['slug'] for d in data['datasets']]
            data['expression'] = {k: dataset_expr[k] for k in ordered_keys}
        return data


class OrthologCountSerializer(serializers.ModelSerializer):
    species = serializers.CharField(source='species__scientific_name')
    gene_count = serializers.IntegerField(source='count')

    class Meta:
        model = models.Ortholog
        fields = ['species', 'gene_count']


class AlignRequestSerializer(serializers.Serializer):
    sequences = serializers.CharField(
        required=True,
        help_text=f"The FASTA sequences to query (maximum of {settings.MAX_ALIGNMENT_SEQS} sequences).")
    type = serializers.ChoiceField(
        choices=('aminoacids', 'nucleotides'), required=True,
        help_text="The monomers used in the sequences: either <kbd>aminoacids</kbd> for proteins (default) or <kbd>nucleotides</kbd> for DNA/RNA.")
    species = serializers.ChoiceField(
        choices=[
            (s.scientific_name, s.common_name)
            for s in models.Species.objects.filter(files__title='DIAMOND')
        ] if check_model_exists(models.Species) else [],
        required=True,
        help_text="The [species' scientific name](#/operations/species_list).")


class AlignResponseSerializer(serializers.Serializer):
    query = serializers.CharField(help_text="ID of the query sequence")
    target = serializers.CharField(help_text="ID of the hit sequence")
    identity = serializers.FloatField(help_text="Percentage of identity between query and hit sequences")
    length = serializers.IntegerField(help_text="Length of the alignment")
    mismatch = serializers.IntegerField(help_text="Number of mismatches in the alignment")
    gaps = serializers.IntegerField(help_text="Number of gaps in the alignment")
    query_start = serializers.IntegerField(help_text="Start position of the query sequence in the alignment")
    query_end = serializers.IntegerField(help_text="End position of the query sequence in the alignment")
    target_start = serializers.IntegerField(help_text="Start position of the hit sequence in the alignment")
    target_end = serializers.IntegerField(help_text="End position of the hit sequence in the alignment")
    e_value = serializers.FloatField(help_text="Statistical significance")
    bit_score = serializers.FloatField(help_text="Alignment quality")
