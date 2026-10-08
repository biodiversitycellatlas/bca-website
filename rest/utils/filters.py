"""Helper functions for django-filter filters."""

import logging

from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_filters.rest_framework import ChoiceFilter

from app import models

logger = logging.getLogger(__name__)


def check_model_exists(model):
    try:
        return model._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


def skip_param(queryset, name, value):
    """
    Document a query parameter without altering the queryset.
    Useful if the actual param is altered elsewhere.
    """
    return queryset


_cached_species_choices = None


def update_species_choices():
    """Update species choices, cached until species change."""
    global _cached_species_choices

    if _cached_species_choices is None:
        choices = []
        if check_model_exists(models.Species):
            try:
                choices = [
                    (s.scientific_name, s.common_name if s.common_name is not None else s.get_html())
                    for s in models.Species.objects.all()
                ]
                choices = sorted(choices, key=lambda x: x[0])
                _cached_species_choices = choices
            except Exception as exc:
                logger.debug("Could not update species choices: %s", exc)
    else:
        choices = _cached_species_choices

    return choices


_cached_dataset_choices = None


def update_dataset_choices():
    """Update dataset choices, cached until datasets change."""
    global _cached_dataset_choices

    if _cached_dataset_choices is None:
        choices = []
        if check_model_exists(models.Dataset):
            try:
                choices = [(d.slug, str(d)) for d in models.Dataset.objects.all()]
                choices = sorted(choices, key=lambda x: x[0])
                _cached_dataset_choices = choices
            except Exception as exc:
                logger.debug("Could not update dataset choices: %s", exc)
    else:
        choices = _cached_dataset_choices

    return choices


@receiver([post_save, post_delete], sender=models.Species)
def invalidate_species_choices(**_kwargs):
    """Clear cached species choices when species change."""
    global _cached_species_choices
    _cached_species_choices = None


@receiver([post_save, post_delete], sender=models.Dataset)
def invalidate_dataset_choices(**_kwargs):
    """Clear cached dataset choices when datasets change."""
    global _cached_dataset_choices
    _cached_dataset_choices = None


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
