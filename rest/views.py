from rest_framework import viewsets, pagination
from rest_framework.exceptions import NotFound
from django.db.models import Prefetch

from . import serializers, filters
from app import models


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """ List available species. """
    queryset = models.Species.objects.prefetch_related('meta_set')
    serializer_class = serializers.SpeciesSerializer
    filterset_class = filters.SpeciesFilter
    lookup_field = 'scientific_name'


class GeneViewSet(viewsets.ReadOnlyModelViewSet):
    """ List genes. """
    queryset = models.Gene.objects.prefetch_related('species')
    serializer_class = serializers.GeneSerializer
    filterset_class = filters.GeneFilter
    lookup_field = 'name'


class OrthologViewSet(viewsets.ReadOnlyModelViewSet):
    """ List gene orthologs. """
    queryset = models.Ortholog.objects.all()
    serializer_class = serializers.OrthologSerializer
    lookup_field = 'orthogroup'
    filterset_class = filters.OrthologFilter


class ExpressionPrefetchMixin:
    """ Mixin to prefetch gene expression for single cell and metacell views. """

    related_field = 'singlecellgeneexpression'
    expression_related_name = 'singlecellgeneexpression_set'
    expression_model = models.SingleCellGeneExpression

    def get_queryset(self):
        gene = self.request.query_params.get('gene', None)
        species = self.request.query_params.get('species', None)

        if species and gene:
            # Check if gene expression data for the selected gene exists
            filters = {f"{self.related_field}__gene__name": gene}
            if not self.queryset.filter(**filters).exists():
                raise NotFound(f"No gene expression data found for {gene} in {species}")

            # Prefetch gene expression
            queryset = self.queryset.prefetch_related(
                Prefetch(
                    self.expression_related_name,
                    queryset=self.expression_model.objects.filter(gene__name=gene),
                    to_attr = 'gene_expression'
                )
            )
            return queryset
        return self.queryset


class SingleCellViewSet(ExpressionPrefetchMixin, viewsets.ReadOnlyModelViewSet):
    """ List single cells for a given species. """
    queryset = models.SingleCell.objects.prefetch_related('metacell')
    serializer_class = serializers.SingleCellSerializer
    filterset_class = filters.SingleCellFilter
    lookup_field = 'name'

class MetacellViewSet(ExpressionPrefetchMixin, viewsets.ReadOnlyModelViewSet):
    """ List metacells for a given species. """
    queryset = models.Metacell.objects.prefetch_related('type')
    serializer_class = serializers.MetacellSerializer
    filterset_class = filters.MetacellFilter
    lookup_field = 'name'

    related_field = 'metacellgeneexpression'
    expression_related_name = 'metacellgeneexpression_set'
    expression_model = models.MetacellGeneExpression


class MetacellLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """ List metacell links for a given species. """
    queryset = models.MetacellLink.objects.prefetch_related('metacell', 'metacell2')
    serializer_class = serializers.MetacellLinkSerializer
    filterset_class = filters.MetacellLinkFilter


class MetacellGeneExpressionViewSet(viewsets.ReadOnlyModelViewSet):
    """ Retrieve gene expression data per metacell. """
    queryset = models.MetacellGeneExpression.objects.prefetch_related('metacell', 'gene')
    serializer_class = serializers.MetacellGeneExpressionSerializer
    filterset_class = filters.MetacellGeneExpressionFilter


class SingleCellGeneExpressionViewSet(viewsets.ReadOnlyModelViewSet):
    """ Retrieve gene expression data per single cell. """
    queryset = models.SingleCellGeneExpression.objects.prefetch_related('single_cell', 'gene')
    serializer_class = serializers.SingleCellGeneExpressionSerializer
    filterset_class = filters.SingleCellGeneExpressionFilter


class MetacellMarkerViewSet(viewsets.ReadOnlyModelViewSet):
    """ Retrieve gene markers of selected metacells. """
    # Gene as model (easier to perform gene-wise operations)
    queryset = models.Gene.objects.all()
    serializer_class = serializers.MetacellMarkerSerializer
    filterset_class = filters.MetacellMarkerFilter
