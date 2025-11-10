"""
REST API serializers.
"""

from operator import attrgetter

from django.conf import settings
from django.db.models import Avg, Max, Min, StdDev, Sum
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from app import models

from .aggregates import PercentileCont
from .utils import check_model_exists


class MetaSerializer(serializers.ModelSerializer):
    """Species metadata serializer."""

    source = serializers.CharField(help_text="Metadata source.")

    class Meta:
        """Meta configuration."""

        model = models.Meta
        fields = ["key", "value", "source", "query_url"]


class FileSerializer(serializers.ModelSerializer):
    """Species file serializer."""

    class Meta:
        """Meta configuration."""

        model = models.File
        fields = ["type", "file", "checksum"]


class SourceSerializer(serializers.ModelSerializer):
    """Source serializer."""

    class Meta:
        """Meta configuration."""

        model = models.Source
        exclude = ["id"]


class DatasetSerializer(serializers.ModelSerializer):
    """Dataset serializer."""

    source = SourceSerializer()
    species = serializers.CharField(
        source="species.scientific_name", help_text="Species name."
    )
    dataset = serializers.CharField(source="name", help_text="Dataset name.")
    dataset_html = serializers.CharField(
        source="get_html_link", help_text="HTML representation of the dataset."
    )
    species_common_name = serializers.CharField(source="species.common_name")
    species_image_url = serializers.CharField(source="species.image_url")
    species_description = serializers.CharField(source="species.description")
    species_meta = MetaSerializer(
        source="species.meta_set", many=True, help_text="Species metadata."
    )
    species_html = serializers.CharField(source="species.get_html_link")
    slug = serializers.CharField(help_text="Dataset slug.")

    class Meta:
        """Meta configuration."""

        model = models.Dataset
        fields = [
            "species",
            "dataset",
            "slug",
            "dataset_html",
            "description",
            "image_url",
            "source",
            "order",
            "date_created",
            "date_updated",
            "species_common_name",
            "species_html",
            "species_image_url",
            "species_description",
            "species_meta",
        ]


class SpeciesSerializer(serializers.ModelSerializer):
    """Serializer for Species model."""

    meta = MetaSerializer(source="meta_set", many=True, help_text="Species metadata.")
    files = FileSerializer(many=True, help_text="Supporting files.")
    datasets = DatasetSerializer(
        many=True, help_text="Available datasets for the species."
    )
    html = serializers.CharField(source="get_html_link")

    class Meta:
        """Meta configuration."""

        model = models.Species
        fields = [
            "common_name",
            "scientific_name",
            "html",
            "description",
            "image_url",
            "meta",
            "files",
            "datasets",
        ]


class SummaryStatsSerializer(serializers.ModelSerializer):
    """Serializer for summary statistics model."""

    min = serializers.FloatField(help_text="Minimum value.")
    q1 = serializers.FloatField(help_text="First quartile (Q1) value.")
    avg = serializers.FloatField(help_text="Average value.")
    median = serializers.FloatField(help_text="Median value.")
    q3 = serializers.FloatField(help_text="Third quartile (Q3) value.")
    max = serializers.FloatField(help_text="Maximum value.")
    stddev = serializers.FloatField(help_text="Standard deviation.")

    class Meta:
        """Meta configuration."""

        model = models.Dataset
        fields = ["min", "q1", "avg", "median", "q3", "max", "stddev"]


class DatasetQualityControlSerializer(serializers.ModelSerializer):
    """Dataset quality control serializer."""

    type = serializers.CharField(
        source="metric.type", help_text="Quality control type."
    )
    metric = serializers.CharField(
        source="metric.name", help_text="Quality control metric."
    )
    description = serializers.CharField(
        source="metric.description", help_text="Quality control description."
    )

    class Meta:
        """Meta configuration."""

        model = models.DatasetQualityControl
        fields = ["type", "metric", "description", "value"]


class StatsSerializer(serializers.ModelSerializer):
    """Statistics serializer."""

    species = serializers.CharField(
        source="species.scientific_name", help_text="Species scientific name."
    )
    dataset = serializers.CharField(source="name", help_text="Dataset name.")
    cells = serializers.SerializerMethodField(help_text="Number of cells.")
    metacells = serializers.SerializerMethodField(help_text="Number of metacells.")
    umis = serializers.SerializerMethodField(
        help_text="Number of unique molecular identifiers (UMIs)."
    )
    genes = serializers.SerializerMethodField(help_text="Number of genes.")

    umis_per_metacell = serializers.SerializerMethodField(
        help_text="Summary statistics on UMIs per metacell."
    )
    cells_per_metacell = serializers.SerializerMethodField(
        help_text="Summary statistics on cells per metacell."
    )

    qc_metrics = DatasetQualityControlSerializer(
        source="qc.all", many=True, help_text="Quality control metrics."
    )

    class Meta:
        """Meta configuration."""

        model = models.Dataset
        fields = [
            "species",
            "dataset",
            "genes",
            "cells",
            "metacells",
            "umis",
            "umis_per_metacell",
            "cells_per_metacell",
            "qc_metrics",
        ]

    def get_metacell_counts(self, obj):
        """Return metacell counts for the dataset."""
        return models.MetacellCount.objects.filter(metacell__dataset=obj.id)

    def get_cells(self, obj) -> int:
        """Return number of single cells in the dataset."""
        return models.SingleCell.objects.filter(dataset=obj.id).count()

    def get_metacells(self, obj) -> int:
        """Return number of metacells in the dataset."""
        return models.Metacell.objects.filter(dataset=obj.id).count()

    def get_umis(self, obj) -> int:
        """Return sum of UMIs in the dataset."""
        res = self.get_metacell_counts(obj).aggregate(Sum("umis")).values()
        return list(res)[0]

    def get_genes(self, obj) -> int:
        """Return total number of genes in the dataset."""
        return models.Gene.objects.filter(species__datasets=obj.id).count()

    def calculate_stats(self, obj, field):
        """Calculate statistical summary for a given field."""
        counts = self.get_metacell_counts(obj)

        stats = counts.aggregate(
            min=Min(field),
            q1=PercentileCont(field, percentile=0.25),
            avg=Avg(field),
            median=PercentileCont(field, percentile=0.50),
            q3=PercentileCont(field, percentile=0.75),
            max=Max(field),
            stddev=StdDev(field),
        )
        return stats

    @extend_schema_field(SummaryStatsSerializer)
    def get_cells_per_metacell(self, obj) -> int:
        """Return statistical summary of cells per metacell."""
        return self.calculate_stats(obj, "cells")

    @extend_schema_field(SummaryStatsSerializer)
    def get_umis_per_metacell(self, obj) -> int:
        """Return statistical summary of UMIs per metacell."""
        return self.calculate_stats(obj, "umis")


class GeneSerializer(serializers.ModelSerializer):
    """Gene serializer."""

    species = serializers.CharField(required=False)
    genelists = serializers.StringRelatedField(many=True)
    domains = serializers.StringRelatedField(many=True)
    orthogroup = serializers.CharField()

    class Meta:
        """Meta configuration."""

        model = models.Gene
        fields = [
            "species",
            "name",
            "description",
            "domains",
            "genelists",
            "orthogroup",
        ]

    def __init__(self, *args, **kwargs):
        """Object initializer."""

        # Do not show 'species' in result if filtered in query params
        if "context" in kwargs and "request" in kwargs["context"]:
            species = kwargs["context"]["request"].GET.get("species", None)

            if species:
                self.fields.pop("species")

        super().__init__(*args, **kwargs)


class DomainSerializer(serializers.ModelSerializer):
    """Protein domain serializer."""

    gene_count = serializers.IntegerField(required=False)

    class Meta:
        """Meta configuration."""

        model = models.Domain
        fields = ["name", "gene_count"]


class GeneListSerializer(serializers.ModelSerializer):
    """Gene list serializer."""

    gene_count = serializers.SerializerMethodField(required=False)

    def get_gene_count(self, obj) -> int:
        """Return number of genes in gene list."""

        genes = obj.genes
        species = self.context.get("request").query_params.get("species", None)
        if species:
            genes = genes.filter(species__scientific_name=species)
        return genes.count()

    class Meta:
        """Meta configuration."""

        model = models.GeneList
        fields = ["name", "description", "gene_count"]


class GeneModuleSerializer(serializers.ModelSerializer):
    """Gene module serializer."""

    dataset = serializers.CharField(source="dataset.slug")
    module = serializers.CharField(source="name")
    gene_count = serializers.IntegerField(source="genes.count")

    class Meta:
        """Meta configuration."""

        model = models.GeneModule
        fields = ["dataset", "module", "gene_count"]


class GeneModuleMembershipSerializer(serializers.ModelSerializer):
    """Gene module membership serializer."""

    gene = serializers.CharField()
    module = serializers.CharField()
    dataset = serializers.CharField(source="module.dataset.slug")
    score = serializers.CharField(source="membership_score")

    class Meta:
        """Meta configuration."""

        model = models.GeneModuleMembership
        fields = ["dataset", "module", "gene", "score"]


class GeneModuleEigenvalueSerializer(serializers.ModelSerializer):
    """Gene module eigenvalue serializer."""

    metacell = serializers.CharField()
    module = serializers.CharField()
    dataset = serializers.CharField(source="module.dataset.slug")
    eigenvalue = serializers.CharField()

    class Meta:
        """Meta configuration."""

        model = models.GeneModuleEigenvalue
        fields = ["dataset", "module", "metacell", "eigenvalue"]


class BaseExpressionSerializer(serializers.ModelSerializer):
    """Base class to display gene expression for single cell and metacell serializers."""

    # Show expression data for a given gene
    expression_fields = ["gene_name", "umi_raw", "umifrac", "fold_change"]
    gene_name = serializers.SerializerMethodField(required=False)
    umi_raw = serializers.SerializerMethodField(required=False)
    umifrac = serializers.SerializerMethodField(required=False)

    def __init__(self, *args, **kwargs):
        """Object initializer."""

        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not (request and request.query_params.get("gene")):
            for field in self.expression_fields:
                self.fields.pop(field, None)

    def get_expression_value(self, obj, field):
        """Retrieve field from gene expression data (e.g., umi_raw)."""

        gene = self.context["request"].GET.get("gene")
        if gene and obj.gene_expression:
            return attrgetter(field)(obj.gene_expression[0])
        return None

    def get_gene_name(self, obj):
        """Return gene name."""
        return self.context["request"].GET.get("gene")

    def get_umi_raw(self, obj):
        """Return raw UMI."""
        return self.get_expression_value(obj, "umi_raw")

    def get_umifrac(self, obj):
        """Return UMI fraction."""
        return self.get_expression_value(obj, "umifrac")

    def get_fold_change(self, obj):
        """Return fold-change value."""
        return self.get_expression_value(obj, "fold_change")


class SingleCellSerializer(BaseExpressionSerializer):
    """Single cell serializer."""

    # Default is null for single cells with no metacell
    metacell_name = serializers.CharField(source="metacell.name", default=None)
    metacell_type = serializers.CharField(source="metacell.type.name", default=None)
    metacell_color = serializers.CharField(source="metacell.type.color", default=None)

    class Meta:
        """Meta configuration."""

        model = models.SingleCell
        fields = [
            "name",
            "x",
            "y",
            "metacell_name",
            "metacell_type",
            "metacell_color",
            "gene_name",
            "umifrac",
            "umi_raw",
        ]


class MetacellSerializer(BaseExpressionSerializer):
    """Metacell serializer."""

    type = serializers.CharField(
        source="type.name", help_text="Metacell type.", required=False
    )
    color = serializers.CharField(
        source="type.color", help_text="Color of metacell type.", required=False
    )

    # Show expression for a given gene
    fold_change = serializers.SerializerMethodField(required=False)

    class Meta:
        """Meta configuration."""

        model = models.Metacell
        fields = [
            "name",
            "x",
            "y",
            "type",
            "color",
            "gene_name",
            "fold_change",
            "umifrac",
            "umi_raw",
        ]


class MetacellLinkSerializer(serializers.ModelSerializer):
    """Metacell link serializer."""

    metacell = serializers.CharField(source="metacell.name")
    metacell_x = serializers.FloatField(source="metacell.x")
    metacell_y = serializers.FloatField(source="metacell.y")
    metacell2 = serializers.CharField(source="metacell2.name")
    metacell2_x = serializers.FloatField(source="metacell2.x")
    metacell2_y = serializers.FloatField(source="metacell2.y")

    class Meta:
        """Meta configuration."""

        model = models.MetacellLink
        fields = [
            "metacell",
            "metacell_x",
            "metacell_y",
            "metacell2",
            "metacell2_x",
            "metacell2_y",
        ]


class MetacellCountSerializer(serializers.ModelSerializer):
    """Metacell count serializer."""

    metacell = serializers.CharField(source="metacell.name")
    metacell_type = serializers.CharField(source="metacell.type.name")
    metacell_color = serializers.CharField(source="metacell.type.color")

    cells = serializers.IntegerField(help_text="Cell count.")
    umis = serializers.IntegerField(help_text="UMI count.")

    class Meta:
        """Meta configuration."""

        model = models.MetacellCount
        fields = ["metacell", "metacell_type", "metacell_color", "cells", "umis"]


class SingleCellGeneExpressionSerializer(serializers.ModelSerializer):
    """Serializer for gene expression per single cell."""

    gene_name = serializers.CharField(source="gene.name")
    gene_description = serializers.CharField(source="gene.description")
    gene_domains = serializers.StringRelatedField(source="gene.domains", many=True)

    single_cell_name = serializers.CharField(source="single_cell.name")

    class Meta:
        """Meta configuration."""

        model = models.SingleCellGeneExpression
        exclude = ["id", "dataset"]


class MetacellGeneExpressionSerializer(serializers.ModelSerializer):
    """Serializer for gene expression for each metacell."""

    log2_fold_change = serializers.FloatField(required=False)

    gene_name = serializers.CharField(source="gene.name")
    gene_description = serializers.CharField(source="gene.description")
    gene_domains = serializers.StringRelatedField(source="gene.domains", many=True)

    metacell_name = serializers.CharField(source="metacell.name")
    metacell_type = serializers.CharField(source="metacell.type.name")
    metacell_color = serializers.CharField(source="metacell.type.color")

    class Meta:
        """Meta configuration."""

        model = models.MetacellGeneExpression
        exclude = ["dataset", "id", "gene", "metacell"]


class DatasetMetacellGeneExpressionSerializer(MetacellGeneExpressionSerializer):
    """Serializer for gene expression per metacell (returned per dataset)."""

    dataset = serializers.CharField(source="dataset.slug")

    gene_name = None
    gene_description = None
    gene_domains = None

    class Meta:
        """Meta configuration."""

        model = MetacellGeneExpressionSerializer.Meta.model
        exclude = ["id", "gene", "metacell"]


class CorrelatedGenesSerializer(serializers.ModelSerializer):
    """Serializer for correlated genes."""

    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    domains = serializers.SerializerMethodField()
    spearman = serializers.FloatField()
    pearson = serializers.FloatField()

    class Meta:
        """Meta configuration."""

        model = models.GeneCorrelation
        exclude = ["dataset", "id", "gene", "gene2"]

    def get_non_selected_gene(self, obj):
        """Return non-selected gene."""

        selected = self.context["request"].query_params.get("gene")
        # Return the gene that was not selected in the input
        return obj.gene2 if obj.gene.name == selected else obj.gene

    def get_name(self, obj) -> str:
        """Return gene name from non-selected gene."""

        gene = self.get_non_selected_gene(obj)
        return gene.name

    def get_description(self, obj) -> str:
        """Return gene description from non-selected gene."""

        gene = self.get_non_selected_gene(obj)
        return gene.description

    def get_domains(self, obj) -> list[str]:
        """Return domains from non-selected gene."""

        gene = self.get_non_selected_gene(obj)
        return [domain.name for domain in gene.domains.all()]


class MetacellMarkerSerializer(serializers.ModelSerializer):
    """Serializer for metacell markers."""

    # Parse name of domains and gene lists
    domains = serializers.StringRelatedField(many=True)
    genelists = serializers.StringRelatedField(many=True)

    bg_sum_umi = serializers.FloatField()
    fg_sum_umi = serializers.FloatField()
    umi_perc = serializers.FloatField()
    fg_mean_fc = serializers.FloatField()
    fg_median_fc = serializers.FloatField()

    class Meta:
        """Meta configuration."""

        model = models.Gene
        exclude = ["species", "correlations"]


class OrthologSerializer(serializers.ModelSerializer):
    """Ortholog gene serializer."""

    species = serializers.CharField()

    gene_name = serializers.CharField(source="gene.name")
    gene_description = serializers.CharField(source="gene.description")
    gene_domains = serializers.StringRelatedField(source="gene.domains", many=True)
    gene_slug = serializers.CharField(source="gene.slug")

    expression = DatasetMetacellGeneExpressionSerializer(
        source="gene.mge", many=True, required=False
    )

    class Meta:
        """Meta configuration."""

        model = models.Ortholog
        exclude = ["id", "gene"]

    def __init__(self, *args, **kwargs):
        """Object initializer."""

        show_expression = (
            kwargs["context"]["request"].GET.get("expression", "false") == "true"
        )
        if not show_expression:
            self.fields.pop("expression")
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        """Return object representation."""
        data = super().to_representation(instance)

        # Split expression by dataset
        if self.fields.get("expression"):
            all_datasets = {d.slug: d for d in models.Dataset.objects.all()}

            dataset_expr = {}
            dataset_dict = {}
            for item in data["expression"]:
                dataset = item.pop("dataset")
                if dataset not in dataset_dict:
                    dataset_dict[dataset] = all_datasets[dataset]
                dataset_expr.setdefault(dataset, []).append(item)

            # Add dataset information
            data["datasets"] = DatasetSerializer(
                list(dataset_dict.values()), many=True
            ).data

            # Sort datasets by their order
            data["datasets"].sort(key=lambda x: x["order"])
            ordered_keys = [d["slug"] for d in data["datasets"]]
            data["expression"] = {k: dataset_expr[k] for k in ordered_keys}
        return data


class OrthologCountSerializer(serializers.ModelSerializer):
    """Serializer for ortholog count."""

    species = serializers.CharField(source="species__scientific_name")
    gene_count = serializers.IntegerField(source="count")

    class Meta:
        """Meta configuration."""

        model = models.Ortholog
        fields = ["species", "gene_count"]


class SAMapSerializer(serializers.ModelSerializer):
    """Serializer for SAMap scores."""

    dataset = serializers.SerializerMethodField()
    dataset2 = serializers.SerializerMethodField()
    metacell_type = serializers.SerializerMethodField()
    metacell2_type = serializers.SerializerMethodField()
    metacell_color = serializers.SerializerMethodField()
    metacell2_color = serializers.SerializerMethodField()
    samap = serializers.FloatField()

    class Meta:
        """Meta configuration."""

        model = models.SAMap
        fields = [
            "dataset",
            "metacell_type",
            "metacell_color",
            "dataset2",
            "metacell2_type",
            "metacell2_color",
            "samap",
        ]

    def _get_metacell_types(self, obj):
        """Return metacell types."""
        # Swap datasets according to input
        if getattr(obj, "order_flag", 0) == 1:
            return obj.metacelltype2, obj.metacelltype
        return obj.metacelltype, obj.metacelltype2

    def get_dataset(self, obj) -> str:
        """Return dataset for metacell 1."""
        return self._get_metacell_types(obj)[0].dataset.slug

    def get_dataset2(self, obj) -> str:
        """Return dataset for metacell 2."""
        return self._get_metacell_types(obj)[1].dataset.slug

    def get_metacell_type(self, obj) -> str:
        """Return metacell type for metacell 1."""
        return self._get_metacell_types(obj)[0].name

    def get_metacell2_type(self, obj) -> str:
        """Return metacell type for metacell 2."""
        return self._get_metacell_types(obj)[1].name

    def get_metacell_color(self, obj) -> str:
        """Return metacell color for metacell 1."""
        return self._get_metacell_types(obj)[0].color

    def get_metacell2_color(self, obj) -> str:
        """Return metacell color for metacell 2."""
        return self._get_metacell_types(obj)[1].color


class AlignRequestSerializer(serializers.Serializer):
    """Serializer for sequence alignment request."""

    sequences = serializers.CharField(
        required=True,
        help_text=(
            f"The FASTA sequences to query (maximum of {settings.MAX_ALIGNMENT_SEQS} sequences)."
        ),
    )
    type = serializers.ChoiceField(
        choices=("aminoacids", "nucleotides"),
        required=True,
        help_text=(
            "The monomers used in the sequences: either <kbd>aminoacids</kbd> "
            "for proteins (default) or <kbd>nucleotides</kbd> for DNA/RNA."
        ),
    )
    species = serializers.ChoiceField(
        choices=(
            [
                (s.scientific_name, s.common_name)
                for s in models.Species.objects.filter(files__type="DIAMOND")
            ]
            if check_model_exists(models.Species)
            else []
        ),
        required=True,
        help_text="The [species' scientific name](#/operations/species_list).",
    )


class AlignResponseSerializer(serializers.Serializer):
    """Serializer for sequence alignment response."""

    query = serializers.CharField(help_text="ID of the query sequence.")
    target = serializers.CharField(help_text="ID of the hit sequence.")
    identity = serializers.FloatField(
        help_text="Percentage of identity between query and hit sequences."
    )
    length = serializers.IntegerField(help_text="Length of the alignment.")
    mismatch = serializers.IntegerField(
        help_text="Number of mismatches in the alignment."
    )
    gaps = serializers.IntegerField(help_text="Number of gaps in the alignment.")
    query_start = serializers.IntegerField(
        help_text="Start position of the query sequence in the alignment."
    )
    query_end = serializers.IntegerField(
        help_text="End position of the query sequence in the alignment."
    )
    target_start = serializers.IntegerField(
        help_text="Start position of the hit sequence in the alignment."
    )
    target_end = serializers.IntegerField(
        help_text="End position of the hit sequence in the alignment."
    )
    e_value = serializers.FloatField(help_text="Statistical significance.")
    bit_score = serializers.FloatField(help_text="Alignment quality.")
