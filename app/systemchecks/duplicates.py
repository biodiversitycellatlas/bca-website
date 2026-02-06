from typing import List, Type, Any

from django.core import checks
from django.core.checks import register, Error
from django.db.models import Count

from app.models import Gene, Domain


@register(checks.Tags.files, deploy=True)
def check_duplicates(app_configs, **kwargs) -> List[Error]:
    errors = []

    classes = [Domain, Gene]
    for cls in classes:
        errors.extend(collect_duplicates(cls))

    return errors


def collect_duplicates(cls: Type[Any]) -> List[Error]:
    errors = []
    entities = cls.objects.values("name").annotate(count=Count("name")).exclude(count=1)
    for entity in entities:
        errors.append(Error(msg="Duplicate found", hint="duplicate entity", obj=entity, id="bca.E004"))
    return errors
