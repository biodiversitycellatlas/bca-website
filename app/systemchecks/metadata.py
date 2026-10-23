from django.core import checks
from django.core.checks import Error, register

from app.management.metadata_existence import check_metadata_existence


@register(checks.Tags.files, deploy=True)
def check_metadata(app_configs, **kwargs) -> list[Error]:
    return check_metadata_existence()
