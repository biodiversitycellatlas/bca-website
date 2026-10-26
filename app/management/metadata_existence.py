from django.core.checks import Error
from django.db.models.aggregates import Sum

from app.models import Dataset, DatasetQualityControl, Gene, Metacell, MetacellCount, QualityControl, SingleCell


def check_metadata_existence() -> list[Error]:
    """Checks the existence of metadata values in all datasets"""

    errors = []
    for dset in Dataset.objects.all():
        sizes = {}
        sizes["cells"] = SingleCell.objects.filter(dataset=dset).count()
        sizes["metacells"] = Metacell.objects.filter(dataset=dset).count()
        sizes["genes"] = Gene.objects.filter(species=dset.species).count()
        sizes["umis"] = MetacellCount.objects.filter(dataset=dset).aggregate(Sum("umis"))["umis__sum"]

        for key, value in sizes.items():
            if value is None or value == 0:
                errors.append(
                    Error(
                        msg=f"The number of {key} must be positive in dataset {dset}",
                        hint="metadata entries",
                        obj=dset,
                        id="bca.E004",
                    )
                )

        for qc in QualityControl.objects.all():
            dqcs = list(DatasetQualityControl.objects.filter(dataset=dset))
            dqcs_names = [e.metric.name for e in dqcs]
            dqcs_values = [e.value for e in dqcs]
            dqcs_dict = dict(zip(dqcs_names, dqcs_values))
            if qc.name not in dqcs_names:
                errors.append(
                    Error(
                        msg=f"Missing Metric {qc.name} In dataset {dset} ",
                        hint="metadata entries",
                        obj=dset,
                        id="bca.E004",
                    )
                )
            else:
                if dqcs_dict[qc.name] is None or len(dqcs_dict[qc.name]) < 3:
                    errors.append(
                        Error(
                            msg=f"Metric {qc.name} does not have a proper value {dqcs_dict[qc.name]} in dataset {dset}",
                            hint="metadata entries",
                            obj=dset,
                            id="bca.E004",
                        )
                    )
    return errors
