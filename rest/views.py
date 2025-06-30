from rest_framework import viewsets, pagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from django.db.models import Prefetch, Count
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Case, When, Value, IntegerField

from . import serializers, filters
from .utils import parse_species_dataset, get_enum_description, get_path_param

from app import models

import re
import os
import subprocess
import tempfile
from urllib.parse import unquote_plus


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
class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Species.objects.prefetch_related('meta_set')
    serializer_class = serializers.SpeciesSerializer
    filterset_class = filters.SpeciesFilter
    lookup_field = 'scientific_name'
    lookup_url_kwarg = 'species'

    def get_object(self):
        self.kwargs[self.lookup_url_kwarg] = unquote_plus(self.kwargs[self.lookup_url_kwarg])
        return super().get_object()

    @extend_schema(
        summary="Retrieve species information",
        description="Retrieve information for a given species",
        tags=["Species"],
        parameters=[ get_path_param('species', filters.SpeciesChoiceFilter) ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    summary="List datasets",
    tags=["Dataset"],
    parameters=[
        OpenApiParameter(
            'q', str,
            description="Query string to filter results. The string will be searched and ranked across dataset's name and description.",
            examples=[ OpenApiExample(
                'Example', value='adult'
            ) ])
    ]
)
class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Dataset.objects.all()
    serializer_class = serializers.DatasetSerializer
    filterset_class = filters.DatasetFilter
    lookup_field = 'slug'
    lookup_url_kwarg = 'dataset'

    def get_object(self):
        return parse_species_dataset( self.kwargs.get("dataset") )

    @extend_schema(
        summary="Retrieve dataset information",
        description="Retrieve information for a given dataset",
        tags=["Dataset"],
        parameters=[ get_path_param('dataset', filters.DatasetChoiceFilter) ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    summary="List dataset statistics",
    tags=["Dataset"]
)
class StatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Dataset.objects.all()
    serializer_class = serializers.StatsSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'dataset'

    def get_object(self):
        return parse_species_dataset( self.kwargs.get("dataset") )

    @extend_schema(
        summary="Retrieve dataset statistics",
        description="Retrieve statistics for a given dataset",
        tags=["Dataset"],
        parameters=[ get_path_param('dataset', filters.DatasetChoiceFilter) ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
    tags=["Gene", "Cross-species"]
)
class OrthologViewSet(BaseReadOnlyModelViewSet):
    """ List gene orthologs. """
    queryset = models.Ortholog.objects.prefetch_related(
        'gene', 'gene__mge', 'gene__mge__dataset',
        'gene__mge__metacell', 'gene__mge__metacell__type')
    serializer_class = serializers.OrthologSerializer
    lookup_field = 'orthogroup'
    filterset_class = filters.OrthologFilter


@extend_schema(
    summary="List SAMap scores",
    tags=["Cross-species"]
)
class SAMapViewSet(BaseReadOnlyModelViewSet):
    """ List SAMap alignment scores (in percentage) between cell types of two different datasets. """
    queryset = models.SAMap.objects.prefetch_related(
        'metacelltype', 'metacelltype__dataset',
        'metacelltype2', 'metacelltype2__dataset')
    serializer_class = serializers.SAMapSerializer
    filterset_class = filters.SAMapFilter

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        dataset_slug = self.request.query_params.get('dataset')
        dataset2_slug = self.request.query_params.get('dataset2')
        if not dataset_slug or not dataset2_slug:
            return queryset

        ds1 = parse_species_dataset(dataset_slug)
        ds2 = parse_species_dataset(dataset2_slug)

        qs = queryset.annotate(
            order_flag=Case(
                When(metacelltype__dataset=ds1, metacelltype2__dataset=ds2, then=Value(0)),
                When(metacelltype__dataset=ds2, metacelltype2__dataset=ds1, then=Value(1)),
                default=Value(2),  # fallback
                output_field=IntegerField()
            )
        ).order_by('order_flag')
        return qs


@extend_schema(
    summary="List ortholog counts",
    tags=["Gene"]
)
class OrthologCountViewSet(BaseReadOnlyModelViewSet):
    """ List ortholog gene counts per species (ordered by count). """
    queryset = models.Ortholog.objects.all()
    serializer_class = serializers.OrthologCountSerializer
    filterset_class = filters.OrthologCountFilter

    def get_queryset(self):
        orthogroup = self.request.query_params.get('orthogroup')
        if orthogroup and not self.queryset.filter(orthogroup=orthogroup).exists():
            raise NotFound(detail=f"Orthogroup '{orthogroup}' not found.")

        qs = self.queryset.values('species__scientific_name').annotate(
            count=Count('id')).order_by('-count')
        return qs


class ExpressionPrefetchMixin:
    """ Mixin to prefetch gene expression for single cell and metacell views. """

    related_field = 'scge'
    expression_related_name = 'scge'
    expression_model = models.SingleCellGeneExpression

    def get_queryset(self):
        gene = self.request.query_params.get('gene', None)
        dataset = self.request.query_params.get('dataset', None)

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
    """ List single cells for a given dataset. """
    queryset = models.SingleCell.objects.prefetch_related(
        'metacell', 'metacell__type')
    serializer_class = serializers.SingleCellSerializer
    filterset_class = filters.SingleCellFilter
    lookup_field = 'name'


@extend_schema(
    summary="List metacells",
    tags=["Metacell"]
)
class MetacellViewSet(ExpressionPrefetchMixin, BaseReadOnlyModelViewSet):
    """ List metacells for a given dataset. """
    queryset = models.Metacell.objects.prefetch_related('type')
    serializer_class = serializers.MetacellSerializer
    filterset_class = filters.MetacellFilter
    lookup_field = 'name'

    related_field = 'mge'
    expression_related_name = 'mge'
    expression_model = models.MetacellGeneExpression


@extend_schema(
    summary="List metacell links",
    tags=["Metacell"]
)
class MetacellLinkViewSet(BaseReadOnlyModelViewSet):
    """ List metacell links (visualised in projections) for a given dataset. """
    queryset = models.MetacellLink.objects.prefetch_related('metacell', 'metacell2')
    serializer_class = serializers.MetacellLinkSerializer
    filterset_class = filters.MetacellLinkFilter


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
        'single_cell', 'gene', 'gene__domains', 'metacell', 'metacell__type')
    serializer_class = serializers.SingleCellGeneExpressionSerializer
    filterset_class = filters.SingleCellGeneExpressionFilter


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
        'metacell', 'metacell__type', 'gene', 'gene__domains')
    serializer_class = serializers.MetacellGeneExpressionSerializer
    filterset_class = filters.MetacellGeneExpressionFilter


@extend_schema(
    summary="List correlated genes",
    tags=["Gene"],
    parameters=[
        OpenApiParameter(
            'ordering', str,
            description=get_enum_description(
                filters.CorrelatedGenesFilter().base_filters['ordering'].label,
                dict(filters.CorrelatedGenesFilter().base_filters['ordering'].extra['choices'])),
            enum=dict(filters.CorrelatedGenesFilter().base_filters['ordering'].extra['choices']),
            examples=[ OpenApiExample( 'Example', value='-pearson_r' ) ])
    ]
)
class CorrelatedGenesViewSet(BaseReadOnlyModelViewSet):
    """ List correlated genes for a given gene and dataset. """
    queryset = models.GeneCorrelation.objects.all()
    serializer_class = serializers.CorrelatedGenesSerializer
    filterset_class = filters.CorrelatedGenesFilter


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
    queryset = models.Gene.objects.prefetch_related('domains', 'genelists')

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
    queryset = models.MetacellCount.objects.prefetch_related(
        'metacell', 'metacell__type')
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
        db = s.files.filter(type='DIAMOND')

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
