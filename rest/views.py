import logging
import os
import subprocess
import tempfile
from urllib.parse import unquote_plus
from itertools import combinations, chain

from django.conf import settings
from django.db.models import Case, Count, IntegerField, Prefetch, Value, When
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import viewsets, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from app.managers import ExpressionDataManager
from app import models
from . import filters, serializers
from .utils import get_enum_description, get_path_param, parse_species_dataset, group_by_key


class BaseReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    @extend_schema(exclude=True)
    def retrieve(self, request, *args, **kwargs):
        # Skip the original retrieve behavior
        raise NotImplementedError("This method was not implemented.")


@extend_schema(
    summary="List species",
    tags=["Species"],
    parameters=[
        OpenApiParameter(
            "q",
            str,
            description="Query string to filter results. The string will be searched and "
            + "ranked across species' common name, scientific name and metadata.",
            examples=[OpenApiExample("Example", value="mouse")],
        )
    ],
)
class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Species.objects.prefetch_related("meta_set")
    serializer_class = serializers.SpeciesSerializer
    filterset_class = filters.SpeciesFilter
    lookup_field = "scientific_name"
    lookup_url_kwarg = "species"

    def get_object(self):
        self.kwargs[self.lookup_url_kwarg] = unquote_plus(self.kwargs[self.lookup_url_kwarg])
        return super().get_object()

    @extend_schema(
        summary="Retrieve species information",
        description="Retrieve information for a given species",
        tags=["Species"],
        parameters=[get_path_param("species", filters.SpeciesChoiceFilter)],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    summary="List datasets",
    tags=["Dataset"],
    parameters=[
        OpenApiParameter(
            "q",
            str,
            description="Query string to filter results. The string will be searched "
            + "and ranked across dataset's name and description.",
            examples=[OpenApiExample("Example", value="adult")],
        )
    ],
)
class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Dataset.objects.all()
    serializer_class = serializers.DatasetSerializer
    filterset_class = filters.DatasetFilter
    lookup_field = "slug"
    lookup_url_kwarg = "dataset"

    def get_object(self):
        return parse_species_dataset(self.kwargs.get("dataset"))

    @extend_schema(
        summary="Retrieve dataset information",
        description="Retrieve information for a given dataset",
        tags=["Dataset"],
        parameters=[get_path_param("dataset", filters.DatasetChoiceFilter)],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(summary="List dataset statistics", tags=["Dataset"])
class StatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Dataset.objects.all()
    serializer_class = serializers.StatsSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "dataset"

    def get_object(self):
        return parse_species_dataset(self.kwargs.get("dataset"))

    @extend_schema(
        summary="Retrieve dataset statistics",
        description="Retrieve statistics for a given dataset",
        tags=["Dataset"],
        parameters=[get_path_param("dataset", filters.DatasetChoiceFilter)],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    summary="List protein domains",
    tags=["Gene"],
    parameters=[
        OpenApiParameter(
            "q",
            str,
            description=filters.DomainFilter().base_filters["q"].label,
            examples=[OpenApiExample("Example", value="kinase")],
        ),
    ],
)
class DomainViewSet(BaseReadOnlyModelViewSet):
    """List protein domains."""

    queryset = models.Domain.objects.all()
    serializer_class = serializers.DomainSerializer
    filterset_class = filters.DomainFilter
    lookup_field = "name"


@extend_schema(summary="List preset lists of genes", tags=["Gene"])
class GeneListViewSet(BaseReadOnlyModelViewSet):
    """List preset lists of genes, such as transcription factors."""

    queryset = models.GeneList.objects.all()
    serializer_class = serializers.GeneListSerializer
    filterset_class = filters.GeneListFilter
    lookup_field = "name"


@extend_schema(summary="List gene modules", tags=["Gene module"])
class GeneModuleViewSet(BaseReadOnlyModelViewSet):
    """List gene modules."""

    queryset = models.GeneModule.objects.all()
    serializer_class = serializers.GeneModuleSerializer
    filterset_class = filters.GeneModuleFilter
    lookup_field = "name"


@extend_schema(summary="List gene module membership", tags=["Gene module"])
class GeneModuleMembershipViewSet(BaseReadOnlyModelViewSet):
    """List gene membership in gene modules."""

    queryset = models.GeneModuleMembership.objects.prefetch_related("module", "module__dataset", "gene")
    serializer_class = serializers.GeneModuleMembershipSerializer
    filterset_class = filters.GeneModuleMembershipFilter
    lookup_field = "name"


@extend_schema(
    summary="List gene module similarity",
    tags=["Gene module"],
)
class GeneModuleSimilarityViewSet(BaseReadOnlyModelViewSet):
    """List similarity between all gene modules in a dataset."""

    queryset = models.GeneModule.objects.prefetch_related("membership")
    serializer_class = serializers.GeneModuleSimilaritySerializer
    filterset_class = filters.GeneModuleSimilarityFilter
    lookup_field = "name"
    pagination_class = None

    def serialize_genes(self, ids, info, html=False):
        """
        Serialize gene objects from a list of IDs.

        Args:
            ids (list): List of gene IDs.
            info (dict): Mapping of gene ID to gene object.
            html (bool, optional): If True, return HTML code with links to objects.

        Returns:
            list: Serialized gene data.
        """
        genes = [g for g in map(info.get, ids) if g]
        s = serializers.GeneTableSerializer if html else serializers.GeneSerializer
        return s(genes, many=True).data

    def compute_gene_overlap(self, dataset, m1, m1_genes, m2, m2_genes, genes_info, list_genes=False, html=False):
        """
        Compute overlap statistics between two gene modules.

        Args:
            dataset (str): Dataset name.
            m1 (str): First module name.
            m1_genes (set): Genes in first module.
            m2 (str): Second module name.
            m2_genes (set): Genes in second module.
            genes_info (dict): Mapping of gene ID to gene object.
            list_genes (bool, optional): If True, include serialized gene lists
                for unique and intersecting genes.
            html (bool, optional): If True, return HTML code with links to objects.

        Returns:
            dict: Overlap statistics including similarity percentage,
            counts of unique/intersecting genes, and optionally gene lists.
        """
        unique_m1 = m1_genes - m2_genes
        unique_m2 = m2_genes - m1_genes
        intersecting = m1_genes & m2_genes
        union = m1_genes | m2_genes

        unique_m1_values = len(unique_m1)
        unique_m2_values = len(unique_m2)
        intersecting_values = len(intersecting)
        union_values = len(union)

        elem = {
            "dataset": dataset,
            "module": m1,
            "dataset2": dataset,
            "module2": m2,
            "similarity": round(intersecting_values / union_values * 100) if union_values > 0 else 0,
            "intersecting_genes": intersecting_values,
            "unique_genes_module": unique_m1_values,
            "unique_genes_module2": unique_m2_values,
        }

        if list_genes:
            elem.update(
                {
                    "unique_genes_module_list": self.serialize_genes(unique_m1, genes_info, html),
                    "unique_genes_module2_list": self.serialize_genes(unique_m2, genes_info, html),
                    "intersecting_genes_list": self.serialize_genes(intersecting, genes_info, html),
                }
            )
        return elem

    def compare_within_dataset(self, dataset, module=None, module2=None, list_genes=False, html=False):
        """Compare pairwise gene overlaps within a dataset."""
        modules = dataset.gene_modules.prefetch_related("genes")
        module_genes = group_by_key(modules, "name", "genes__name")

        genes_info = {g.id: g for m in modules.all() for g in m.genes.all()}

        # Calculate for each unique combination (avoid calculating overlaps twice)
        overlaps = []
        pairs = combinations(module_genes.items(), 2)

        for (m1, m1_genes), (m2, m2_genes) in pairs:
            if module and module not in (m1, m2):
                continue
            elif module2 and module2 not in (m1, m2):
                continue

            o = self.compute_gene_overlap(dataset, m1, m1_genes, m2, m2_genes, genes_info, list_genes, html)
            overlaps.append(o)
        return overlaps

    def compare_within_species(self, dataset, dataset2, module=None, module2=None, list_genes=False, html=False):
        """Compare pairwise gene overlaps between two datasets of the same species."""
        d1_modules = dataset.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_genes = group_by_key(d1_modules, "name", "genes")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_genes = group_by_key(d2_modules, "name", "genes")

        modules = list(d1_modules.all()) + list(d2_modules.all())
        genes_info = {g.id: g for m in modules for g in m.genes.all()}

        overlaps = []
        for m1, m1_genes in d1_module_genes.items():
            for m2, m2_genes in d2_module_genes.items():
                o = self.compute_gene_overlap(dataset, m1, m1_genes, m2, m2_genes, genes_info, list_genes, html)
                overlaps.append(o)
        return overlaps

    def compute_orthogroup_overlap(self, d1, m1, m1_orthogroups, d2, m2, m2_orthogroups, genes_info, list_genes=False, html=False):
        """
        Compute overlap statistics between two modules using orthogroup mappings.

        Args:
            d1 (str): First dataset name.
            m1 (str): First module name.
            m1_orthogroups (dict): Mapping orthogroup → list of genes for module 1.
            d2 (str): Second dataset name.
            m2 (str): Second module name.
            m2_orthogroups (dict): Mapping orthogroup → list of genes for module 2.
            genes_info (dict): Mapping of gene ID to gene object.
            list_genes (bool, optional): If True, include serialized gene lists
                for unique and intersecting genes. Defaults to False.
            html (bool, optional): If True, return HTML code with links to objects.

        Returns:
            dict: Overlap statistics based on orthogroups, including similarity
            percentage, counts of unique/intersecting genes, and optionally gene lists.
        """
        m1_ogs = m1_orthogroups.keys() - {None}
        m2_ogs = m2_orthogroups.keys() - {None}

        # Calculate intersecting orthogroups
        unique_m1_ogs = m1_ogs - m2_ogs
        unique_m2_ogs = m2_ogs - m1_ogs
        intersecting_ogs = m1_ogs & m2_ogs

        # Retrieve corresponding genes
        unique_m1 = list(chain.from_iterable(m1_orthogroups.get(i, []) for i in unique_m1_ogs))
        unique_m1 += list(m1_orthogroups.get(None, []))  # include genes without orthogroups
        unique_m2 = list(chain.from_iterable(m2_orthogroups.get(i, []) for i in unique_m2_ogs))
        unique_m2 += list(m2_orthogroups.get(None, []))  # include genes without orthogroups
        intersecting_m1 = list(chain.from_iterable(m1_orthogroups.get(i, []) for i in intersecting_ogs))
        intersecting_m2 = list(chain.from_iterable(m2_orthogroups.get(i, []) for i in intersecting_ogs))
        intersecting = intersecting_m1 + intersecting_m2

        # Count values
        unique_m1_values = len(unique_m1)
        unique_m2_values = len(unique_m2)
        intersecting_values = len(intersecting)

        # Assuming previous values are correct, this is quicker but equal to:
        # sum([len(i) for i in m1_orthogroups.values()]) + sum([len(i) for i in m2_orthogroups.values()])
        union_values = unique_m1_values + unique_m2_values + intersecting_values

        elem = {
            "dataset": d1,
            "module": m1,
            "dataset2": d2,
            "module2": m2,
            "similarity": round(intersecting_values / union_values * 100) if union_values > 0 else 0,
            "intersecting_genes": intersecting_values,
            "unique_genes_module": unique_m1_values,
            "unique_genes_module2": unique_m2_values,
        }

        if list_genes:
            elem.update(
                {
                    "unique_genes_module_list": self.serialize_genes(unique_m1, genes_info, html),
                    "unique_genes_module2_list": self.serialize_genes(unique_m2, genes_info, html),
                    "intersecting_genes_list": self.serialize_genes(intersecting, genes_info, html),
                    "intersecting_genes_module_list": self.serialize_genes(intersecting_m1, genes_info, html),
                    "intersecting_genes_module2_list": self.serialize_genes(intersecting_m2, genes_info, html),
                }
            )
        return elem

    def compare_across_species(self, dataset, dataset2, module=None, module2=None, list_genes=False, html=False):
        """Compare pairwise orthogroup overlaps for each gene across species."""
        d1_modules = dataset.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_orthogroups = group_by_key(d1_modules, "name", "genes__orthogroup", "genes__name")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_orthogroups = group_by_key(d2_modules, "name", "genes__orthogroup", "genes__name")

        modules = list(d1_modules.all()) + list(d2_modules.all())
        genes_info = {g.id: g for m in modules for g in m.genes.all()}

        overlaps = []
        for m1, m1_orthogroups in d1_module_orthogroups.items():
            for m2, m2_orthogroups in d2_module_orthogroups.items():
                o = self.compute_orthogroup_overlap(
                    dataset, m1, m1_orthogroups, dataset2, m2, m2_orthogroups, genes_info, list_genes, html
                )
                overlaps.append(o)
        return overlaps

    def list(self, request, *args, **kwargs):
        # Parse query parameters
        dataset_slug = self.request.query_params.get("dataset")
        dataset2_slug = self.request.query_params.get("dataset2") or dataset_slug  # if undefined, use dataset
        module = self.request.query_params.get("module")
        module2 = self.request.query_params.get("module2")
        list_genes = self.request.query_params.get("list_genes") in ["true", "1", "True"]
        sort_modules = self.request.query_params.get("sort_modules") in ["true", "1", "True"]
        html = self.request.query_params.get("html") in ["true", "1", "True"]

        dataset = parse_species_dataset(dataset_slug)
        dataset2 = parse_species_dataset(dataset2_slug)

        # Check if gene modules exist
        for m, d in ((module, dataset), (module2, dataset2)):
            if m is not None and not d.gene_modules.filter(name=m).exists():
                raise ValueError(f"Error: module {m} does not exist in {d}")

        # Different comparison methods of gene module similarity
        if dataset == dataset2:
            overlaps = self.compare_within_dataset(dataset, module, module2, list_genes, html)
        elif dataset.species == dataset2.species:
            overlaps = self.compare_within_species(dataset, dataset2, module, module2, list_genes, html)
        else:
            overlaps = self.compare_across_species(dataset, dataset2, module, module2, list_genes, html)

        # Sort modules based on highest similarity score
        if sort_modules:
            overlaps = sorted(overlaps, key=lambda x: x["similarity"], reverse=True)

        serializer = self.get_serializer(overlaps, many=True)
        return Response(serializer.data)


@extend_schema(summary="List module eigengenes", tags=["Gene module"])
class GeneModuleEigengeneViewSet(BaseReadOnlyModelViewSet):
    """List module eigengene values for each metacell."""

    queryset = models.GeneModuleEigengene.objects.prefetch_related(
        "module", "module__dataset", "metacell", "metacell__type"
    )
    serializer_class = serializers.GeneModuleEigengeneSerializer
    filterset_class = filters.GeneModuleEigengeneFilter
    lookup_field = "name"


@extend_schema(
    summary="List genes",
    tags=["Gene"],
    parameters=[
        OpenApiParameter(
            "genes",
            str,
            description=filters.GeneFilter().base_filters["genes"].label,
            examples=[OpenApiExample("Example", value="Transcription factors,Pkinase,Tadh_P33902")],
        ),
        OpenApiParameter(
            "q",
            str,
            description=filters.GeneFilter().base_filters["q"].label,
            examples=[OpenApiExample("Example", value="ATP binding")],
        ),
    ],
)
class GeneViewSet(BaseReadOnlyModelViewSet):
    """List genes."""

    queryset = models.Gene.objects.prefetch_related("species", "domains")
    serializer_class = serializers.GeneSerializer
    filterset_class = filters.GeneFilter
    lookup_field = "name"


@extend_schema(summary="List orthologs", tags=["Gene", "Cross-species"])
class OrthologViewSet(BaseReadOnlyModelViewSet):
    """List gene orthologs."""

    queryset = models.Ortholog.objects.prefetch_related(
        "gene",
        "gene__mge",
        "gene__mge__dataset",
        "gene__mge__metacell",
        "gene__mge__metacell__type",
    )
    serializer_class = serializers.OrthologSerializer
    lookup_field = "orthogroup"
    filterset_class = filters.OrthologFilter


@extend_schema(summary="List SAMap scores", tags=["Cross-species"])
class SAMapViewSet(BaseReadOnlyModelViewSet):
    """List SAMap alignment scores (in percentage) between cell types of two different datasets."""

    queryset = models.SAMap.objects.prefetch_related(
        "metacelltype",
        "metacelltype__dataset",
        "metacelltype2",
        "metacelltype2__dataset",
    )
    serializer_class = serializers.SAMapSerializer
    filterset_class = filters.SAMapFilter

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        dataset_slug = self.request.query_params.get("dataset")
        dataset2_slug = self.request.query_params.get("dataset2")
        if not dataset_slug or not dataset2_slug:
            return queryset

        ds1 = parse_species_dataset(dataset_slug)
        ds2 = parse_species_dataset(dataset2_slug)

        qs = queryset.annotate(
            order_flag=Case(
                When(metacelltype__dataset=ds1, metacelltype2__dataset=ds2, then=Value(0)),
                When(metacelltype__dataset=ds2, metacelltype2__dataset=ds1, then=Value(1)),
                default=Value(2),  # fallback
                output_field=IntegerField(),
            )
        ).order_by("order_flag")
        return qs


@extend_schema(summary="List ortholog counts", tags=["Gene"])
class OrthologCountViewSet(BaseReadOnlyModelViewSet):
    """List ortholog gene counts per species (ordered by count)."""

    queryset = models.Ortholog.objects.all()
    serializer_class = serializers.OrthologCountSerializer
    filterset_class = filters.OrthologCountFilter

    def get_queryset(self):
        orthogroup = self.request.query_params.get("orthogroup")
        if orthogroup and not self.queryset.filter(orthogroup=orthogroup).exists():
            raise NotFound(detail=f"Orthogroup '{orthogroup}' not found.")

        qs = self.queryset.values("species__scientific_name").annotate(count=Count("id")).order_by("-count")
        return qs


class ExpressionPrefetchMixin:
    """Mixin to prefetch gene expression for metacell views."""

    related_field = "mge"
    expression_related_name = "mge"
    expression_model = models.MetacellGeneExpression

    def get_queryset(self):
        gene = self.request.query_params.get("gene", None)
        dataset = self.request.query_params.get("dataset", None)

        if dataset and gene:
            # Check if gene expression data for the selected gene exists
            filters = {f"{self.related_field}__gene__name": gene}
            if not self.queryset.filter(**filters).exists():
                raise NotFound(f"No gene expression data found for {gene} in {dataset}")

            # Prefetch gene expression
            queryset = self.queryset.prefetch_related(
                Prefetch(
                    self.expression_related_name,
                    queryset=self.expression_model.objects.filter(gene__name=gene),
                    to_attr="gene_expression",
                )
            )
            return queryset
        return self.queryset


@extend_schema(summary="List single cells", tags=["Single cell"])
class SingleCellViewSet(BaseReadOnlyModelViewSet):
    """List single cells for a given dataset."""

    queryset = models.SingleCell.objects.prefetch_related("metacell", "metacell__type")
    serializer_class = serializers.SingleCellSerializer
    filterset_class = filters.SingleCellFilter
    lookup_field = "name"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        dataset = context["request"].GET.get("dataset")
        gene = context["request"].GET.get("gene")
        if gene is None:
            expression_dictionary = {}
        else:
            expression_data_manager = ExpressionDataManager(dataset, gene)
            expression_dictionary = expression_data_manager.get_expression_dictionary()
        context.update({"expression_dictionary": expression_dictionary})
        return context


@extend_schema(summary="List metacells", tags=["Metacell"])
class MetacellViewSet(ExpressionPrefetchMixin, BaseReadOnlyModelViewSet):
    """List metacells for a given dataset."""

    queryset = models.Metacell.objects.prefetch_related("type")
    serializer_class = serializers.MetacellSerializer
    filterset_class = filters.MetacellFilter
    lookup_field = "name"


@extend_schema(summary="List metacell links", tags=["Metacell"])
class MetacellLinkViewSet(BaseReadOnlyModelViewSet):
    """List metacell links (visualised in projections) for a given dataset."""

    queryset = models.MetacellLink.objects.prefetch_related("metacell", "metacell2")
    serializer_class = serializers.MetacellLinkSerializer
    filterset_class = filters.MetacellLinkFilter


@extend_schema(
    summary="List gene expression per single cell",
    tags=["Single cell", "Gene"],
    request=serializers.SingleCellGeneExpressionSerializer,
    parameters=[
        OpenApiParameter(
            "gene",
            int,
            "query",
            True,
            "gene name",
            examples=[OpenApiExample("Example", value="Spolac_c99997_g1")],
        ),
        OpenApiParameter(
            "dataset",
            int,
            "query",
            True,
            "dataset slug",
            examples=[OpenApiExample("Example", value="spongilla-lacustris")],
        ),
    ],
)
class SingleCellGeneExpressionViewSet(viewsets.GenericViewSet):
    """List single-cell expression data for a gene in a dataset."""

    http_method_names = ["get"]
    serializer_class = serializers.SingleCellGeneExpressionSerializer
    queryset = models.SingleCellGeneExpression.objects.none()
    filterset_class = None
    pagination_class = None

    def list(self, request, *args, **kwargs):
        gene = request.query_params.get("gene")
        dataset = request.query_params.get("dataset")
        expression_data_manager = ExpressionDataManager(dataset, gene)
        try:
            data = expression_data_manager.create_singlecellexpression_models()
            serializer = self.get_serializer(instance=data, many=True)
            return Response(serializer.data)
        except OSError:
            logging.exception(f"Error reading expression data for {gene} in {dataset}")
            return Response("detail: error reading expression data", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="List gene expression per metacell",
    tags=["Metacell", "Gene"],
    parameters=[
        OpenApiParameter(
            "genes",
            str,
            description=filters.MetacellGeneExpressionFilter().base_filters["genes"].label,
            examples=[OpenApiExample("Example", value="Transcription factors,Pkinase,Tadh_P33902")],
        ),
        OpenApiParameter(
            "metacells",
            str,
            description=filters.MetacellGeneExpressionFilter().base_filters["metacells"].label,
            examples=[OpenApiExample("Example", value="12,30,Peptidergic1")],
        ),
    ],
)
class MetacellGeneExpressionViewSet(BaseReadOnlyModelViewSet):
    """List gene expression data per metacell."""

    queryset = models.MetacellGeneExpression.objects.prefetch_related(
        "metacell", "metacell__type", "gene", "gene__domains"
    )
    serializer_class = serializers.MetacellGeneExpressionSerializer
    filterset_class = filters.MetacellGeneExpressionFilter


@extend_schema(
    summary="List correlated genes",
    tags=["Gene"],
    parameters=[
        OpenApiParameter(
            "ordering",
            str,
            description=get_enum_description(
                filters.CorrelatedGenesFilter().base_filters["ordering"].label,
                dict(filters.CorrelatedGenesFilter().base_filters["ordering"].extra["choices"]),
            ),
            enum=dict(filters.CorrelatedGenesFilter().base_filters["ordering"].extra["choices"]),
            examples=[OpenApiExample("Example", value="-pearson_r")],
        )
    ],
)
class CorrelatedGenesViewSet(BaseReadOnlyModelViewSet):
    """List correlated genes for a given gene and dataset."""

    queryset = models.GeneCorrelation.objects.all()
    serializer_class = serializers.CorrelatedGenesSerializer
    filterset_class = filters.CorrelatedGenesFilter


@extend_schema(
    summary="List cell type markers",
    tags=["Metacell"],
    parameters=[
        OpenApiParameter(
            name="metacells",
            type=str,
            location="query",
            required=True,
            description=filters.MetacellMarkerFilter().base_filters["metacells"].label,
            examples=[OpenApiExample("Example", value="12,30,Peptidergic1")],
        )
    ],
)
class MetacellMarkerViewSet(BaseReadOnlyModelViewSet):
    """List gene markers of selected metacells."""

    # Gene as model (easier to perform gene-wise operations)
    queryset = models.Gene.objects.prefetch_related("domains", "genelists")

    serializer_class = serializers.MetacellMarkerSerializer
    filterset_class = filters.MetacellMarkerFilter

    @extend_schema(exclude=True)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(summary="List metacell counts", tags=["Metacell"])
class MetacellCountViewSet(BaseReadOnlyModelViewSet):
    queryset = models.MetacellCount.objects.prefetch_related("metacell", "metacell__type")
    serializer_class = serializers.MetacellCountSerializer
    filterset_class = filters.MetacellCountFilter


@extend_schema(
    summary="Submit sequences for alignment",
    description="Align query sequences against the protein sequences in the BCA database "
    + f"using [DIAMOND {settings.DIAMOND_VERSION}](https://github.com/bbuchfink/diamond).",
    tags=["Sequence alignment"],
)
class AlignViewSet(viewsets.ViewSet):
    serializer_class = serializers.AlignRequestSerializer
    limit = settings.MAX_ALIGNMENT_SEQS  # Limit number of sequences to align

    examples = getattr(serializers.AlignRequestSerializer, "_spectacular_annotation", {}).get("examples", [])

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "species",
                str,
                location="query",
                required=True,
                description=serializers.AlignRequestSerializer().fields["species"].help_text,
                examples=[OpenApiExample("Species", value=examples[0].value["species"])],
            ),
            OpenApiParameter(
                "sequences",
                str,
                location="query",
                required=True,
                examples=[OpenApiExample(e.name, value=e.value["sequences"]) for e in examples],
                description=serializers.AlignRequestSerializer().fields["sequences"].help_text,
            ),
            OpenApiParameter(
                "type",
                str,
                location="query",
                required=True,
                enum=serializers.AlignRequestSerializer().fields["type"].choices,
                description=serializers.AlignRequestSerializer().fields["type"].help_text,
            ),
        ],
        operation_id="align_get",
        responses={200: serializers.AlignResponseSerializer(many=True)},
    )
    def list(self, request):
        serializer = self.serializer_class(data=request.query_params)
        return self.process_request(serializer)

    @extend_schema(
        request=serializers.AlignRequestSerializer,
        operation_id="align_post",
        responses={200: serializers.AlignResponseSerializer(many=True)},
    )
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        return self.process_request(serializer)

    def process_request(self, serializer):
        """
        Generalized function to handle both GET and POST requests.
        """
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = self.align(data["species"], data["sequences"], data["type"])
        return Response(result)

    def align(self, species, sequences, type):
        """
        Align query sequences against proteome database from the species.
        """
        s = models.Species.objects.get(scientific_name=species)
        db = s.files.filter(type="DIAMOND").first()

        if db is None:
            raise ValueError(f"{species} does not have a DIAMOND database.")

        # Avoid literal newlines from GET request
        sequences = sequences.replace("\\n", "\n")

        # Check sequence limit
        num_seq = 0
        for line in sequences.splitlines():
            if line.startswith(">"):
                num_seq += 1
                if num_seq > self.limit:
                    raise ValueError(f"Query can only contain up to {self.limit} FASTA sequences")

        program = "blastp" if type in (None, "aminoacids") else "blastx"

        # Write query sequences to temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".fasta") as query_file:
            if not sequences.startswith((">", "@")):
                query_file.write(">query\n")
            query_file.write(sequences)
            query_file.write("\n")
            query_path = query_file.name
        out_path = tempfile.NamedTemporaryFile(suffix=".m8").name

        results = []
        try:
            cmd = [
                "diamond",
                program,
                "--query",
                query_path,
                "--db",
                db.file.path,
                "--out",
                out_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            columns = list(serializers.AlignResponseSerializer().fields.keys())

            with open(out_path) as file:
                for line in file:
                    values = line.strip().split("\t")
                    entry = dict(zip(columns, values))
                    results.append(entry)
        except subprocess.CalledProcessError as e:
            # Raise error if command fails
            raise subprocess.SubprocessError(e.stderr)
        finally:
            # Clean up temporary files
            for f in [query_path, out_path]:
                if os.path.exists(f):
                    os.remove(f)

        return results
