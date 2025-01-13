from rest_framework import serializers
from web_app import models
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample

from operator import attrgetter


class MetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Meta
        fields = ['key', 'value']


class SpeciesSerializer(serializers.ModelSerializer):
    meta = MetaSerializer(source='meta_set', many=True)

    class Meta:
        model = models.Species
        exclude = ['id']


class GeneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Gene
        exclude = ['id', 'species']


class BaseExpressionSerializer(serializers.ModelSerializer):
    """ Base class to display gene expression for single cell and metacell serializers. """
    expression_fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not request.query_params.get('gene'):
            for field in self.expression_fields:
                self.fields.pop(field, None)

    def get_expression_value(self, obj, field):
        """ Retrieve field from expression data (e.g., umi_raw) for query gene. """
        # Get gene from query parameters
        gene = self.context['request'].GET.get('gene')
        if gene:
            filtered = getattr(obj, 'gene_expression', [])
            if filtered:
                return attrgetter(field)(filtered[0])
        return None

    def get_gene_name(self, obj):
        return self.get_expression_value(obj, 'gene.name')


class SingleCellSerializer(BaseExpressionSerializer):
    metacell_name  = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type.name')
    metacell_color = serializers.CharField(source='metacell.type.color')

    # Show expression for a given gene
    umi_raw   = serializers.SerializerMethodField(required=False)
    gene_name = serializers.SerializerMethodField(required=False)
    expression_fields = ['gene_name', 'umi_raw']

    def get_umi_raw(self, obj):
        return self.get_expression_value(obj, 'umi_raw')

    class Meta:
        model = models.SingleCell
        exclude = ['id', 'species']

class MetacellSerializer(BaseExpressionSerializer):
    type  = serializers.CharField(source='type.name')
    color = serializers.CharField(source='type.color')

    # Show expression for a given gene
    fold_change = serializers.SerializerMethodField(required=False)
    gene_name   = serializers.SerializerMethodField(required=False)
    expression_fields = ['gene_name', 'fold_change']

    def get_fold_change(self, obj):
        return self.get_expression_value(obj, 'fold_change')

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
