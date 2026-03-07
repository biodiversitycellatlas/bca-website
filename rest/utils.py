from django.db import connection
from drf_spectacular.utils import OpenApiParameter

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


def group_by_key(queryset, key_field, value_field, extra_field=None):
    """
    Groups values from a queryset by a specified key field.

    Args:
        queryset: Django queryset to extract values from.
        key_field (str): Field name for the dictionary key.
        value_field (str): Field name for the dictionary value.
        extra_field (str, optional): Field name for extra value to nest.

    Returns:
        dict: Dictionary mapping keys to values or dictionary of dictionaries if extra_field is used.
    """
    result = {}
    fields = [key_field, value_field] + ([extra_field] if extra_field else [])

    for values in queryset.values_list(*fields):
        key, value = values[0], values[1]

        if extra_field:
            extra = values[2]
            c = result.setdefault(key, {})
            v = c.setdefault(value, set())
            if extra is not None:  # avoid adding None to get empty set
                v.add(extra)
        else:
            c = result.setdefault(key, set())
            if value is not None:  # avoid adding None to get empty set
                c.add(value)

    return result
