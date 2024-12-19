from rest_framework import permissions, viewsets, pagination
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from django.db.models import (
    Avg,
    Case,
    F,
    FloatField,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
    Sum,
    When,
    Window
)
from django.db.models.functions import Cast, Rank, Log

from . import serializers, filters
from web_app import models


class StandardPagination(pagination.LimitOffsetPagination):
    """ Custom pagination. """
    default_limit = 10
    max_limit = 100

    def get_limit(self, request):
        # Fetch all records if 'limit=0'
        if request.query_params.get('limit') == '0':
            return None
        return super().get_limit(request)

class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """ List available species. """
    queryset = models.Species.objects.all()
    serializer_class = serializers.SpeciesSerializer
    pagination_class = StandardPagination
    lookup_field = 'scientific_name'


class GeneViewSet(viewsets.ReadOnlyModelViewSet):
    """ List genes for a given species. """
    queryset = models.Gene.objects.all()
    serializer_class = serializers.GeneSerializer
    pagination_class = StandardPagination
    filterset_class = filters.GeneFilter
    lookup_field = 'name'


class SingleCellViewSet(viewsets.ReadOnlyModelViewSet):
    """ List single cells for a given species. """
    queryset = models.SingleCell.objects.prefetch_related('metacell')
    serializer_class = serializers.SingleCellSerializer
    pagination_class = StandardPagination
    filterset_class = filters.SingleCellFilter
    lookup_field = 'name'


class MetacellViewSet(viewsets.ReadOnlyModelViewSet):
    """ List metacells for a given species. """
    queryset = models.Metacell.objects.prefetch_related('type')
    serializer_class = serializers.MetacellSerializer
    pagination_class = StandardPagination
    filterset_class = filters.MetacellFilter
    lookup_field = 'name'


class MetacellLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """ List metacell links for a given species. """
    queryset = models.MetacellLink.objects.prefetch_related('metacell', 'metacell2')
    serializer_class = serializers.MetacellLinkSerializer
    pagination_class = StandardPagination
    filterset_class = filters.MetacellLinkFilter


class MetacellGeneExpressionViewSet(viewsets.ReadOnlyModelViewSet):
    """ Retrieve gene expression data per metacell. """
    queryset = models.MetacellGeneExpression.objects.prefetch_related('metacell', 'gene')
    serializer_class = serializers.MetacellGeneExpressionSerializer
    pagination_class = StandardPagination
    filterset_class = filters.MetacellGeneExpressionFilter


class MetacellMarkerViewSet(viewsets.ReadOnlyModelViewSet):
    """ Retrieve gene markers of selected metacells. """
    # Gene as model (easier to perform gene-wise operations)
    queryset = models.Gene.objects.all()
    serializer_class = serializers.MetacellMarkerSerializer
    pagination_class = StandardPagination
    filterset_class = filters.MetacellMarkerFilter
