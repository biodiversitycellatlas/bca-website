from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from operator import attrgetter

from app import models

class MetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Meta
        fields = ['key', 'value']


class SpeciesSerializer(serializers.ModelSerializer):
    meta = MetaSerializer(source='meta_set', many=True)

    class Meta:
        model = models.Species
        fields = ['common_name', 'scientific_name', 'description', 'image_url', 'meta']


class GeneSerializer(serializers.ModelSerializer):
    species = SpeciesSerializer(required=False)
    genelists = serializers.StringRelatedField(many=True)

    class Meta:
        model = models.Gene
        fields = ['name', 'description', 'domains', 'genelists', 'species']

    def __init__(self, *args, **kwargs):
        # Do not show 'species' in result if filtered in query params
        if 'context' in kwargs and 'request' in kwargs['context']:
            species = kwargs['context']['request'].GET.get('species', None)

            if species:
                self.fields.pop('species')

        super().__init__(*args, **kwargs)


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
    metacell_name  = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type.name')
    metacell_color = serializers.CharField(source='metacell.type.color')

    class Meta:
        model = models.SingleCell
        exclude = ['id', 'species']


class MetacellSerializer(BaseExpressionSerializer):
    type  = serializers.CharField(source='type.name')
    color = serializers.CharField(source='type.color')

    # Show expression for a given gene
    fold_change = serializers.SerializerMethodField(required=False)

    class Meta:
        model = models.Metacell
        exclude = ['id', 'species']


class MetacellLinkSerializer(serializers.ModelSerializer):
    metacell  = MetacellSerializer(read_only=True)
    metacell2 = MetacellSerializer(read_only=True)

    class Meta:
        model = models.MetacellLink
        exclude = ['species']


class MetacellGeneExpressionSerializer(serializers.ModelSerializer):
    log2_fold_change = serializers.FloatField(required=False)

    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.ListField(source='gene.domains', child=serializers.CharField())

    metacell_name  = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type.name')
    metacell_color = serializers.CharField(source='metacell.type.color')

    class Meta:
        model = models.MetacellGeneExpression
        exclude = ['species']


class SingleCellGeneExpressionSerializer(serializers.ModelSerializer):
    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.ListField(source='gene.domains', child=serializers.CharField())

    single_cell_name = serializers.CharField(source='single_cell.name')

    class Meta:
        model = models.SingleCellGeneExpression
        exclude = ['species']


class MetacellMarkerSerializer(serializers.ModelSerializer):
    bg_sum_umi = serializers.FloatField()
    fg_sum_umi = serializers.FloatField()
    umi_perc = serializers.FloatField()
    fg_mean_fc = serializers.FloatField()
    fg_median_fc = serializers.FloatField()

    class Meta:
        model = models.Gene
        exclude = ['species']


class OrthologSerializer(serializers.ModelSerializer):
    species = SpeciesSerializer()

    gene_name = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains = serializers.ListField(source='gene.domains', child=serializers.CharField())
    expression = MetacellGeneExpressionSerializer(source='gene.metacellgeneexpression_set', many=True, required=False)

    class Meta:
        model = models.Ortholog
        exclude = ['id']

    def __init__(self, *args, **kwargs):
        show_expression = kwargs['context']['request'].GET.get('expression', 'false') == 'true'
        if not show_expression:
            self.fields.pop('expression')
        super().__init__(*args, **kwargs)
