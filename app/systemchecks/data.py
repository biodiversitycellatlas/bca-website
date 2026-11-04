from django.core import checks
from django.core.checks import Error, register

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
    Gene: ("Gene", True),
    GeneCorrelation: "Gene Correlation",
    GeneModule: "Gene Module",
    Meta: ("Meta", True),
    Metacell: "MetaCell",
    MetacellCount: "Meta Cell Count",
    MetacellGeneExpression: "MetaCell Gene Expression",
    MetacellType: "MetaCell Type",
    Ortholog: ("Ortholog", True),
    SingleCell: "Single Cell",
}

def check_data_existence() -> list[Error]:
    """Checks the existence of values in all datasets"""
    errors = []
    for dset in Dataset.objects.all():
        for model, model_data in datachecks.items():
            use_species = False
            if isinstance(model_data, tuple):
                (model_description, use_species) = model_data
            else:
                model_description = model_data

            if use_species:
                num_entries = model.objects.filter(species=dset.species).count()
            else:
                num_entries = model.objects.filter(dataset=dset).count()

            if num_entries == 0:
                errors.append(
                    Error(
                        msg=f"Dataset {dset} has no records for {model_description}",
                        hint=model_description,
                        obj=dset,
                        id="bca.E005",
                    )
                )
        num_entries = (
            ExpressionConservation.objects.filter(dataset=dset) | ExpressionConservation.objects.filter(dataset2=dset)
        ).count()
        if num_entries == 0:
            errors.append(
                Error(
                    msg=f"Dataset {dset} has no records for Expression Conservation",
                    hint="ExpressionConservation",
                    obj=dset,
                    id="bca.E005",
                )
            )
        num_entries = (
            MetacellTypeSimilarity.objects.filter(metacelltype__dataset=dset)
            | MetacellTypeSimilarity.objects.filter(metacelltype2__dataset=dset)
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
        GeneModuleMembership.objects.filter(module__dataset=dset).count()
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
