from rest_framework import viewsets, pagination

from . import serializers, filters
from web_app import models

class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """ List available species. """
    queryset = models.Species.objects.all()
    serializer_class = serializers.SpeciesSerializer
    lookup_field = 'scientific_name'


class GeneViewSet(viewsets.ReadOnlyModelViewSet):
    """ List genes for a given species. """
    queryset = models.Gene.objects.all()
    serializer_class = serializers.GeneSerializer
    filterset_class = filters.GeneFilter
    lookup_field = 'name'


class OrthologViewSet(viewsets.ReadOnlyModelViewSet):
    """ List gene orthologs. """
    queryset = models.Ortholog.objects.all()
    serializer_class = serializers.OrthologSerializer
    lookup_field = 'orthogroup'
    filterset_class = filters.OrthologFilter


class SingleCellViewSet(viewsets.ReadOnlyModelViewSet):
    """ List single cells for a given species. """
    queryset = models.SingleCell.objects.prefetch_related('metacell')
    serializer_class = serializers.SingleCellSerializer
    filterset_class = filters.SingleCellFilter
    lookup_field = 'name'


class MetacellViewSet(viewsets.ReadOnlyModelViewSet):
    """ List metacells for a given species. """
    queryset = models.Metacell.objects.prefetch_related('type')
    serializer_class = serializers.MetacellSerializer
    filterset_class = filters.MetacellFilter
    lookup_field = 'name'


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


class MetacellMarkerViewSet(viewsets.ReadOnlyModelViewSet):
    """ Retrieve gene markers of selected metacells. """
    # Gene as model (easier to perform gene-wise operations)
    queryset = models.Gene.objects.all()
    serializer_class = serializers.MetacellMarkerSerializer
    filterset_class = filters.MetacellMarkerFilter
