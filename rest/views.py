from rest_framework import viewsets, pagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from django.db.models import Prefetch, Count
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from django.contrib.postgres.aggregates import ArrayAgg

from . import serializers, filters
from app import models

import re
import os
import subprocess
import tempfile


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
            'q', str,
            description="Query string to filter results. The string will be searched and ranked across species' common name, scientific name and metadata.",
            examples=[ OpenApiExample(
                'Example', value='mouse'
            ) ])
    ]
)
class SpeciesViewSet(BaseReadOnlyModelViewSet):
    """ List available species. """
    queryset = models.Species.objects.prefetch_related('meta_set')
    serializer_class = serializers.SpeciesSerializer
    filterset_class = filters.SpeciesFilter
    lookup_field = 'scientific_name'


@extend_schema(
    summary="List species statistics",
    tags=["Species"]
)
class StatsViewSet(BaseReadOnlyModelViewSet):
    queryset = models.Species.objects.all()
    serializer_class = serializers.StatsSerializer
    filterset_class = filters.StatsFilter
    lookup_field = 'scientific_name'


@extend_schema(
    summary="List protein domains",
    tags=["Gene"],
    parameters=[
        OpenApiParameter(
            'q', str,
            description=filters.DomainFilter().base_filters['q'].label,
            examples=[ OpenApiExample(
                'Example', value='kinase'
            ) ]),
    ]
)
class DomainViewSet(BaseReadOnlyModelViewSet):
    """ List protein domains. """
    queryset = models.Domain.objects.all()
    serializer_class = serializers.DomainSerializer
    filterset_class = filters.DomainFilter
    lookup_field = 'name'

    def get_queryset(self):
        qs = self.queryset

        species = self.request.query_params.get('species')
        if species:
            qs = qs.filter(gene__species__scientific_name=species)

        qs = qs.annotate(gene_count=Count('gene', distinct=True))
        return qs

@extend_schema(
    summary="List preset lists of genes",
    tags=["Gene"]
)
class GeneListViewSet(BaseReadOnlyModelViewSet):
    """ List preset lists of genes, such as transcription factors. """
    queryset = models.GeneList.objects.all()
    serializer_class = serializers.GeneListSerializer
    filterset_class = filters.GeneListFilter
    lookup_field = 'name'


@extend_schema(
    summary="List genes",
    tags=["Gene"],
    parameters=[
        OpenApiParameter(
            'genes', str,
            description=filters.GeneFilter().base_filters['genes'].label,
            examples=[ OpenApiExample(
                'Example', value='Transcription factors,Pkinase,Tadh_P33902'
            ) ]),
        OpenApiParameter(
            'q', str,
            description=filters.GeneFilter().base_filters['q'].label,
            examples=[ OpenApiExample(
                'Example', value='ATP binding'
            ) ]),
    ]
)
class GeneViewSet(BaseReadOnlyModelViewSet):
    """ List genes. """
    queryset = models.Gene.objects.prefetch_related('species', 'domains')
    serializer_class = serializers.GeneSerializer
    filterset_class = filters.GeneFilter
    lookup_field = 'name'


@extend_schema(
    summary="List orthologs",
    tags=["Gene"]
)
class OrthologViewSet(BaseReadOnlyModelViewSet):
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


@extend_schema(
    summary="List single cells",
    tags=["Single cell"]
)
class SingleCellViewSet(ExpressionPrefetchMixin, BaseReadOnlyModelViewSet):
    """ List single cells for a given species. """
    queryset = models.SingleCell.objects.prefetch_related('metacell')
    serializer_class = serializers.SingleCellSerializer
    filterset_class = filters.SingleCellFilter
    lookup_field = 'name'


@extend_schema(
    summary="List metacells",
    tags=["Metacell"]
)
class MetacellViewSet(ExpressionPrefetchMixin, BaseReadOnlyModelViewSet):
    """ List metacells for a given species. """
    queryset = models.Metacell.objects.prefetch_related('type')
    serializer_class = serializers.MetacellSerializer
    filterset_class = filters.MetacellFilter
    lookup_field = 'name'

    related_field = 'metacellgeneexpression'
    expression_related_name = 'metacellgeneexpression_set'
    expression_model = models.MetacellGeneExpression


@extend_schema(
    summary="List metacell links",
    tags=["Metacell"]
)
class MetacellLinkViewSet(BaseReadOnlyModelViewSet):
    """ List metacell links for a given species. """
    queryset = models.MetacellLink.objects.prefetch_related('metacell', 'metacell2')
    serializer_class = serializers.MetacellLinkSerializer
    filterset_class = filters.MetacellLinkFilter

@extend_schema(
    summary="List gene expression per metacell",
    tags=["Metacell", "Gene"],
    parameters=[
        OpenApiParameter(
            'genes', str,
            description=filters.MetacellGeneExpressionFilter().base_filters['genes'].label,
            examples=[ OpenApiExample(
                'Example', value='Transcription factors,Pkinase,Tadh_P33902'
            ) ]),
        OpenApiParameter(
            'metacells', str,
            description=filters.MetacellGeneExpressionFilter().base_filters['metacells'].label,
            examples=[ OpenApiExample(
                'Example', value='12,30,Peptidergic1'
            ) ]),
    ]
)
class MetacellGeneExpressionViewSet(BaseReadOnlyModelViewSet):
    """ List gene expression data per metacell. """
    queryset = models.MetacellGeneExpression.objects.prefetch_related(
        'metacell', 'gene', 'gene__domains')
    serializer_class = serializers.MetacellGeneExpressionSerializer
    filterset_class = filters.MetacellGeneExpressionFilter


@extend_schema(
    summary="List gene expression per single cell",
    tags=["Single cell", "Gene"],
    parameters=[
        OpenApiParameter(
            'genes', str,
            description=filters.SingleCellGeneExpressionFilter().base_filters['genes'].label,
            examples=[ OpenApiExample(
                'Example', value='Transcription factors,Pkinase,Tadh_P33902'
            ) ])
    ]
)
class SingleCellGeneExpressionViewSet(BaseReadOnlyModelViewSet):
    """ List gene expression data per single cell. """
    queryset = models.SingleCellGeneExpression.objects.prefetch_related(
        'single_cell', 'gene', 'gene__domains')
    serializer_class = serializers.SingleCellGeneExpressionSerializer
    filterset_class = filters.SingleCellGeneExpressionFilter


@extend_schema(
    summary="List cell type markers",
    tags=["Metacell"],
    parameters=[
        OpenApiParameter(
            'metacells', str,
            description=filters.MetacellMarkerFilter().base_filters['metacells'].label,
            examples=[ OpenApiExample(
                'Example', value='12,30,Peptidergic1'
            ) ])
    ]
)
class MetacellMarkerViewSet(BaseReadOnlyModelViewSet):
    """ List gene markers of selected metacells. """
    # Gene as model (easier to perform gene-wise operations)
    queryset = models.Gene.objects.all()
    serializer_class = serializers.MetacellMarkerSerializer
    filterset_class = filters.MetacellMarkerFilter

    @extend_schema(exclude=True)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    summary="List metacell counts",
    tags=["Metacell"]
)
class MetacellCountViewSet(BaseReadOnlyModelViewSet):
    queryset = models.MetacellCount.objects.prefetch_related('metacell')
    serializer_class = serializers.MetacellCountSerializer
    filterset_class = filters.MetacellCountFilter


@extend_schema(
    summary='Submit sequences for alignment',
    description=f"Align query sequences against the protein sequences in the BCA database using [DIAMOND {settings.DIAMOND_VERSION}](https://github.com/bbuchfink/diamond).",
    tags=["Sequence alignment"]
)
class AlignViewSet(viewsets.ViewSet):
    serializer_class = serializers.AlignRequestSerializer
    limit = settings.MAX_ALIGNMENT_SEQS # Limit number of sequences to align

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'species', str, location='query', required=True,
                enum=serializers.AlignRequestSerializer().fields['species'].choices,
                description=serializers.AlignRequestSerializer().fields['species'].help_text),
            OpenApiParameter(
                'sequences', str, location='query', required=True, examples=[
                    OpenApiExample(
                        'Single query',
                        value='MSIWFSIAILSVLVPFVQLTPIRPRS'
                    ),
                    OpenApiExample(
                        'Multiple queries',
                        summary='Multiple queries',
                        value='>Query_1\\nMSLIRNYNYHLRSASLANASQLDT\\n>Query_2\\nMDSSTDIPCNCVEILTA\\n>Query_3\\nMDSLTDRPCNYVEILTA'
                    )
                ], description=serializers.AlignRequestSerializer().fields['sequences'].help_text),
            OpenApiParameter(
                'type', str, location='query', required=True, enum=serializers.AlignRequestSerializer().fields['type'].choices,
                description=serializers.AlignRequestSerializer().fields['type'].help_text)
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
        result = self.align(data['species'], data['sequences'], data['type'])
        return Response(result)

    def align(self, species, sequences, type):
        """
        Align query sequences against proteome database from the species.
        """
        s = models.Species.objects.filter(scientific_name=species).first()
        db = s.files.filter(title='DIAMOND')

        if not db.exists():
            raise ValueError(f"{species} does not have a DIAMOND database.")
        else:
            db = db.first()

        # Avoid literal newlines from GET request
        sequences = sequences.replace("\\n", "\n")

        # Count lines up to a limit and get a sample from first 10 sequences
        count = 0
        sample = ""
        for line in sequences.splitlines():
            if line.startswith('>'):
                count = count + 1
                if count > self.limit:
                    raise ValueError(f"Query can only contain up to {self.limit} FASTA sequences")
            elif count <= 10:
                sample = sample + line + "\n"

        # Check if sample is composed of amino acids or nucleotides
        program = 'blastp' if (type is None or type == 'aminoacids') else 'blastx'

        # Write query sequences to temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.fasta') as temp_file:
            if not sequences.startswith(">") or not sequences.startswith("@"):
                temp_file.write(">query\n")
            temp_file.write(sequences)
            temp_file.write("\n")
            query_path = temp_file.name
        out_path = tempfile.NamedTemporaryFile(suffix='.m8').name

        results = []
        try:
            cmd = [
                'diamond', program,
                '--query', query_path,
                '--db', db.file.path,
                '--out', out_path
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
