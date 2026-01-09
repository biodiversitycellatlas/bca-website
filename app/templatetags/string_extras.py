"""Custom Django filters and tags to manipulate strings."""

from django import template

register = template.Library()


@register.filter
def split(value, delimiter=","):
    """Split a string by the given delimiter and return a list."""
    return value.split(delimiter)


@register.simple_tag
def startswith(value, arg):
    """Check if the string starts with the given arg string."""
    return value.startswith(arg)


@register.filter
def human_number(value):
    """
    Convert large number into a human-readable string.
    Examples: 1500 -> '2K', 2000000 -> '2M', 950 -> '950'
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value

    if value >= 1_000_000:
        return f"{value/1_000_000:.0f}M"
    elif value >= 1_000:
        return f"{value/1_000:.0f}K"
    else:
        return str(value)


@register.filter
def intspace(value):
    """Convert numeric value to string with spaces as thousand separators."""
    try:
        num = float(value)
        if num.is_integer():
            num = int(num)
        return f"{num:,}".replace(",", " ")
    except (ValueError, TypeError):
        return value
