from rest_framework import serializers
from web_app import models
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


class MetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Meta
        fields = ['key', 'value']


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Species
        exclude = ['id']


class GeneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Gene
        exclude = ['id', 'species']


class MetacellSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Metacell
        exclude = ['id', 'species']


class SingleCellSerializer(serializers.ModelSerializer):
    metacell_name  = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type')
    metacell_color = serializers.CharField(source='metacell.color')

    class Meta:
        model = models.SingleCell
        exclude = ['species']


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
    gene_domains     = serializers.CharField(source='gene.domains')

    metacell_name  = serializers.CharField(source='metacell.name')
    metacell_type  = serializers.CharField(source='metacell.type')
    metacell_color = serializers.CharField(source='metacell.color')

    class Meta:
        model = models.MetacellGeneExpression
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
