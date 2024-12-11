from rest_framework import permissions, viewsets, pagination
from django_filters.rest_framework import DjangoFilterBackend

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
    default_limit = 5
    max_limit = 100


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """ List available species. """
    queryset = models.Species.objects.all()
    serializer_class = serializers.SpeciesSerializer


class GeneViewSet(viewsets.ReadOnlyModelViewSet):
    """ List genes for a given species. """
    queryset = models.Gene.objects.all()
    serializer_class = serializers.GeneSerializer
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.GeneFilter


class MetacellViewSet(viewsets.ReadOnlyModelViewSet):
    """ List metacells for a given species. """
    queryset = models.Metacell.objects.all()
    serializer_class = serializers.MetacellSerializer
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.MetacellFilter


class MetacellGeneExpressionViewSet(viewsets.ReadOnlyModelViewSet):
    """ Prepare gene expression data for heatmap. """
    queryset = models.MetacellGeneExpression.objects.all()
    serializer_class = serializers.MetacellGeneExpressionSerializer
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.MetacellGeneExpressionFilter

