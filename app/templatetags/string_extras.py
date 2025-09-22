"""Custom Django filteres and tags to manipulate strings."""

from django import template

register = template.Library()


@register.filter
def split(value, delimiter=","):
    """Split a string by the given delimiter and return a list."""
    return value.split(delimiter)


@register.simple_tag
def startswith(value, arg):
    """Return True if the string starts with the given argument."""
    return value.startswith(arg)


@register.filter
def intspace(value):
    """If possible, format a numeric value with spaces as thousand separators."""
    try:
        num = float(value)
        if num.is_integer():
            num = int(num)
        return f"{num:,}".replace(",", " ")
    except (ValueError, TypeError):
        return value
