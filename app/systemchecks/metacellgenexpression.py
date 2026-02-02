from typing import List

from django.core.checks import Error, register
from django.core import checks

from app.models import MetacellGeneExpression


@register(checks.Tags.files, deploy=True)
def check_negative_umis(app_configs, **kwargs) -> List[Error]:
    errors = []
    mcgelist = MetacellGeneExpression.objects.filter(umi_raw__lt=0)
    for mcge in mcgelist:
        errors.append(Error(msg="Metacell umi_raw negative value ", hint="negative umi_raw", obj=mcge, id="bca.E002"))
    return errors
