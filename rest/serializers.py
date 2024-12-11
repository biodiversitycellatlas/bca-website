from rest_framework import serializers
from web_app import models
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


class MetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Meta
        fields = ['key', 'value']


class SpeciesSerializer(serializers.HyperlinkedModelSerializer):
    meta = MetaSerializer(many=True, read_only=True, source='meta_set')

    class Meta:
        model = models.Species
        fields = '__all__'


class GeneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Gene
        exclude = ['species']


class MetacellSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Metacell
        exclude = ['species']


class MetacellGeneExpressionSerializer(serializers.ModelSerializer):
    log2_expression = serializers.FloatField()
    gene            = GeneSerializer(read_only=True)
    metacell        = MetacellSerializer(read_only=True)

    class Meta:
        model = models.MetacellGeneExpression
        exclude = ['species']
