from typing import List

from django.apps import apps
from django.core.checks import Error, register
from django.core import checks


MIN_NUM_RECORDS = 4

@register(checks.Tags.files, deploy=True)
def check_tables(app_configs, **kwargs) -> List[Error]:
    errors = []
    models = apps.get_app_config("app").models

    for model in models:
        if model != "singlecellgeneexpression":
            n = len(apps.get_model(f"app.{model}").objects.all()[:MIN_NUM_RECORDS])
            if n < MIN_NUM_RECORDS:
                errors.append(Error(msg="Table has not enough data", hint="few records", obj=model, id="bca.E003"))

    return errors
