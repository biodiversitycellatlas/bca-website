from django.core import checks
from django.core.checks import Error, register
from django.db.models.query_utils import Q

from app.models import (
    CellType,
    Dataset,
    DatasetFile,
    DatasetQualityControl,
    ExpressionConservation,
    Gene,
    GeneCorrelation,
    GeneModule,
    GeneModuleEigengene,
    GeneModuleMembership,
    Meta,
    Metacell,
    MetacellCount,
    MetacellGeneExpression,
    MetacellType,
    MetacellTypeSimilarity,
    Ortholog,
    SingleCell,
)


@register(checks.Tags.files, deploy=True)
def check_data(app_configs, **kwargs) -> list[Error]:
    return check_data_existence()


# Models that need to be queried by species are represented with tuples:
datachecks = {
    CellType: "Cell Type",
    DatasetFile: "Dataset File",
    DatasetQualityControl: "Dataset Quality Control",
    Gene: "Gene",
    GeneCorrelation: "Gene Correlation",
    GeneModule: "Gene Module",
    Meta: "Meta",
    Metacell: "MetaCell",
    MetacellCount: "Meta Cell Count",
    MetacellGeneExpression: "MetaCell Gene Expression",
    MetacellType: "MetaCell Type",
    Ortholog: "Ortholog",
    SingleCell: "Single Cell",
}


def check_data_existence() -> list[Error]:
    """Checks the existence of values in all datasets"""
    errors = []
    for dset in Dataset.objects.all():
        for model, model_description in datachecks.items():
            if hasattr(model, "dataset"):
                num_entries = model.objects.filter(dataset=dset).count()
            else:
                num_entries = model.objects.filter(species=dset.species).count()

            if num_entries == 0:
                errors.append(
                    Error(
                        msg=f"Dataset {dset} has no records for {model_description}",
                        hint=model.__class__.__name__,
                        obj=dset,
                        id="bca.E005",
                    )
                )
        num_entries = (ExpressionConservation.objects.filter(Q(dataset=dset) | Q(dataset2=dset))).count()
        if num_entries == 0:
            errors.append(
                Error(
                    msg=f"Dataset {dset} has no records for Expression Conservation",
                    hint="ExpressionConservation",
                    obj=dset,
                    id="bca.E005",
                )
            )
        num_entries = MetacellTypeSimilarity.objects.filter(
            Q(metacelltype__dataset=dset) | Q(metacelltype2__dataset=dset)
        ).count()
        if num_entries == 0:
            errors.append(
                Error(
                    msg=f"Dataset {dset} has no records for Metacell Type Similarity",
                    hint="MetacellTypeSimilarity",
                    obj=dset,
                    id="bca.E005",
                )
            )
        num_entries = GeneModuleEigengene.objects.filter(module__dataset=dset).count()
        if num_entries == 0:
            errors.append(
                Error(
                    msg=f"Dataset {dset} has no records for GeneModule Eigengene",
                    hint="GeneModuleEigengene",
                    obj=dset,
                    id="bca.E005",
                )
            )
        num_entries = GeneModuleMembership.objects.filter(module__dataset=dset).count()
        if num_entries == 0:
            errors.append(
                Error(
                    msg=f"Dataset {dset} has no records for GeneModule Membership",
                    hint="GeneModuleMembership",
                    obj=dset,
                    id="bca.E005",
                )
            )

    return errors
