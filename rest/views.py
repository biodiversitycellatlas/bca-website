from rest_framework import viewsets, pagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter

from . import serializers, filters
from app import models

import re
import os
import subprocess
import tempfile

class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """ List available species. """
    queryset = models.Species.objects.prefetch_related('meta_set')
    serializer_class = serializers.SpeciesSerializer
    filterset_class = filters.SpeciesFilter
    lookup_field = 'scientific_name'


class GeneListViewSet(viewsets.ReadOnlyModelViewSet):
    """ List gene lists. """
    queryset = models.GeneList.objects.all()
    serializer_class = serializers.GeneListSerializer
    filterset_class = filters.GeneListFilter
    lookup_field = 'name'


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


class AlignViewSet(viewsets.ViewSet):
    """
    Align sequences against the proteins in the BCA database using
    [DIAMOND](https://github.com/bbuchfink/diamond).
    """
    serializer_class = serializers.AlignRequestSerializer
    limit = 100 # Limit number of sequences to align

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'species', str, location='query', required=True,
                description=serializers.AlignRequestSerializer().fields['species'].help_text),
            OpenApiParameter(
                'query', str, location='query', required=True,
                description=serializers.AlignRequestSerializer().fields['query'].help_text),
        ],
        operation_id='align_get',
        responses={200: serializers.AlignResponseSerializer(many=True)},
    )
    def list(self, request):
        serializer = self.serializer_class(data=request.query_params)
        return self.process_request(serializer)

    @extend_schema(
        request=serializers.AlignRequestSerializer,
        operation_id='align_post',
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
        result = self.align(data['species'], data['query'])
        return Response(result)

    def align(self, species, query):
        """
        Align user query against proteome database from the species.
        """
        s = models.Species.objects.filter(scientific_name=species).first()
        db = s.files.filter(title='DIAMOND')

        if not db.exists():
            raise ValueError(f"{species} does not have a DIAMOND database.")
        else:
            db = db.first()

        # Avoid literal newlines from GET request
        query = query.replace("\\n", "\n")

        # Count lines up to a limit and get a sample from first 10 sequences
        count = 0
        sample = ""
        for line in query.splitlines():
            if line.startswith('>'):
                count = count + 1
                if count > self.limit:
                    raise ValueError(f"Query can only contain up to {self.limit} FASTA sequences")
            elif count <= 10:
                sample = sample + line + "\n"

        # Check if sample is composed of amino acids or nucleotides
        if re.search('[DEFHIKLMNPQRSVWY]', sample, re.IGNORECASE):
            type = 'blastp'
        elif re.search('[ACGTU]', sample, re.IGNORECASE):
            type = 'blastx'
        else:
            raise ValueError(f"Query contains invalid characters: {sample}")

        # Write query to temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.fasta') as temp_file:
            if not query.startswith(">") or not query.startswith("@"):
                temp_file.write(">query\n")
            temp_file.write(query)
            temp_file.write("\n")
            query_path = temp_file.name
        out_path = tempfile.NamedTemporaryFile(suffix='.m8').name

        results = []
        try:
            cmd = ['diamond', type, '--query', query_path, '--db', db.file.path, '--out', out_path]
            subprocess.run(cmd, check=True)

            columns = ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
                       "qstart", "qend", "sstart", "send", "evalue", "bitscore"]

            with open(out_path) as file:
                for line in file:
                    values = line.strip().split("\t")
                    entry = dict(zip(columns, values))
                    results.append(entry)
        finally:
            # Clean up temporary files (even if command fails)
            for f in [query_path, out_path]:
                if os.path.exists(f):
                    os.remove(f)

        return results
