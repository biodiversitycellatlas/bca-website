import os
from typing import Type, Any, List

from django.core.checks import Error, register
from django.core import checks

from app.models import DatasetFile, SpeciesFile

MIN_SIZE = 1000


@register(checks.Tags.files, deploy=True)
def check_application_files(app_configs, **kwargs):
    dataset_errors = do_files_exist(DatasetFile)
    species_errors = do_files_exist(SpeciesFile)
    return dataset_errors + species_errors


def do_files_exist(cls: Type[Any]) -> List[Error]:
    """Checks whether all files for the class have a minimum size
    cls is one of the classes {DatasetFile, SpeciesFile}
    """
    errors = []
    for fileobject in cls.objects.all():
        path = fileobject.file.path
        size = os.path.getsize(path)
        if size < MIN_SIZE:
            errors.append(
                Error(
                    "file is has size smaller than {MIN_SIZE} bytes",
                    hint="small file size",
                    obj=path,
                    id="bca.E001",
                )
            )
    return errors
