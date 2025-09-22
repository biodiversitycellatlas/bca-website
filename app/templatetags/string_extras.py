import os
from datetime import datetime

from django import template

register = template.Library()


@register.filter
def split(value, delimiter=","):
    return value.split(delimiter)


@register.simple_tag
def startswith(value, arg):
    """Returns true if the value starts with a given string."""
    return value.startswith(arg)


@register.filter
def intspace(value):
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except (ValueError, TypeError):
        return value
