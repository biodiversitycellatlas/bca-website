"""Helper functions for django-filter filters."""

import logging

from django.db import DatabaseError, connection
from django_filters.rest_framework import ChoiceFilter

from app import models

logger = logging.getLogger(__name__)


def check_model_exists(model):
    try:
        return model._meta.db_table in connection.introspection.table_names()
    except DatabaseError:
        return False


def skip_param(queryset, name, value):
    """
    Document a query parameter without altering the queryset.
    Useful if the actual param is altered elsewhere.
    """
    return queryset


def update_species_choices():
    """Return current species choices."""
    choices = []
    if check_model_exists(models.Species):
        try:
            choices = [
                (s.scientific_name, s.common_name if s.common_name is not None else s.get_html())
                for s in models.Species.objects.all()
            ]
            choices = sorted(choices, key=lambda x: x[0])
        except DatabaseError as exc:
            logger.debug("Could not update species choices: %s", exc)
    return choices


def update_dataset_choices():
    """Return current dataset choices."""
    choices = []
    if check_model_exists(models.Dataset):
        try:
            choices = [(d.slug, str(d)) for d in models.Dataset.objects.all()]
            choices = sorted(choices, key=lambda x: x[0])
        except DatabaseError as exc:
            logger.debug("Could not update dataset choices: %s", exc)
    return choices


def create_fc_type_choice_filter(mode, ignore_mode=False):
    """
    Build a ChoiceFilter for fold-change filtering.

    Args:
        mode (str): "minimum" or "maximum", determines filter type.
        ignore_mode (bool): Whether to include an "ignore" option.

    Returns:
        ChoiceFilter: Configured filter for fold-change thresholding.
    """

    if mode == "minimum":
        var = "fc_min"
        sign = "≥"
        target = "foreground (i.e., selected) metacells"
        default = "mean"
        method = "filter_fc_min"
        required = True
    else:
        var = "bg_fc_max"
        sign = "≤"
        target = "background (i.e., non-selected) metacells"
        default = "ignore"
        method = "filter_fc_max_bg"
        required = False

    choices = [
        [
            item,
            f"Keep genes whose {item} fold-change across {target} {sign} <kbd>{var}</kbd>",
        ]
        for item in ["mean", "median"]
    ]

    if ignore_mode:
        choices.append(["ignore", "Skip this filtering"])

    res = ChoiceFilter(
        choices=choices,
        label=(f"Type of filtering to use for the {mode} fold-change threshold (default: <kbd>{default}</kbd>)."),
        method=method,
        required=required,
    )
    return res
