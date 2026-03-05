from django.db import connection
from drf_spectacular.utils import OpenApiParameter
from collections import Counter

from app.utils import get_dataset


def check_model_exists(model):
    try:
        return model._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


def parse_species_dataset(value):
    dataset = get_dataset(value)
    if not dataset:
        raise ValueError(f"Cannot find dataset for {value}")
    return dataset


def get_enum_description(description, enum):
    """
    Appends list of enumerated values to documentation description.

    Args:
        description (str): The description.
        enum (dict): Dictionary of choices (keys) and their descriptions (values).

    Returns:
        str: Updated description with list of enumerated values.
    """
    new_description = description + "\n\n"
    for key, value in enum.items():
        new_description = new_description + f"* `{key}` - {value}\n"
    return new_description


def get_path_param(name, filter_cls):
    f = filter_cls()
    return OpenApiParameter(
        name,
        str,
        OpenApiParameter.PATH,
        description=get_enum_description(f.label, dict(f.extra["choices"])),
        enum=[i for (i, _) in f.field.choices if i],
    )


def group_by_key(queryset, key_field, value_field, container=set):
    """
    Groups values from a queryset by a specified key field.

    Args:
        queryset: Django queryset to extract values from.
        key_field (str): Field name for the dictionary key.
        value_field (str): Field name for the dictionary value.
        container (type or callable): Type of container for values:
            - list: keep duplicate values
            - set: keeps unique values
            - Counter: count occurrences

    Returns:
        dict: Dictionary mapping keys to value sets (or a single value if flat=True).
    """
    result = {}
    for key, value in queryset.values_list(key_field, value_field):
        obj = container() if callable(container) else container
        c = result.setdefault(key, obj)

        # Store empty object if there are no values
        if value is None:
            continue

        if isinstance(c, Counter):
            c[value] += 1
        elif isinstance(c, set):
            c.add(value)
        else:
            c.append(value)

    return result
