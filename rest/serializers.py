from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer
from django.conf import settings
from operator import attrgetter

from app import models

class MetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Meta
        fields = ['key', 'value']


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.File
        fields = ['title', 'file', 'checksum']


class SpeciesSerializer(serializers.ModelSerializer):
    meta = MetaSerializer(source='meta_set', many=True)
    files = FileSerializer(many=True)

    class Meta:
        model = models.Species
        fields = ['common_name', 'scientific_name', 'description', 'image_url',
                  'meta', 'files']


class GeneSerializer(serializers.ModelSerializer):
    species = SpeciesSerializer(required=False)
    genelists = serializers.StringRelatedField(many=True)
    domains = serializers.StringRelatedField(many=True)

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


class DomainSerializer(serializers.ModelSerializer):
    gene_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.GeneList
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
    metacell    = serializers.CharField(source='metacell.name')
    metacell_x  = serializers.FloatField(source='metacell.x')
    metacell_y  = serializers.FloatField(source='metacell.y')
    metacell2   = serializers.CharField(source='metacell2.name')
    metacell2_x = serializers.FloatField(source='metacell2.x')
    metacell2_y = serializers.FloatField(source='metacell2.y')

    class Meta:
        model = models.MetacellLink
        exclude = ['species']


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
        exclude = ['species']


class SingleCellGeneExpressionSerializer(serializers.ModelSerializer):
    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.StringRelatedField(source='gene.domains',
                                                      many=True)

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

    gene_name        = serializers.CharField(source='gene.name')
    gene_description = serializers.CharField(source='gene.description')
    gene_domains     = serializers.StringRelatedField(source='gene.domains',
                                                      many=True)
    expression = MetacellGeneExpressionSerializer(source='gene.metacellgeneexpression_set', many=True, required=False)

    class Meta:
        model = models.Ortholog
        exclude = ['id']

    def __init__(self, *args, **kwargs):
        show_expression = kwargs['context']['request'].GET.get('expression', 'false') == 'true'
        if not show_expression:
            self.fields.pop('expression')
        super().__init__(*args, **kwargs)


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
        ],
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
