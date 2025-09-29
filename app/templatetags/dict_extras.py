"""Custom Django filters and tags to manipulate dictionaries."""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Return the value for a given key from a dictionary."""
    return dictionary.get(key)
