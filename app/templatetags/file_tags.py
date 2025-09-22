"""Custom Django template filters and tags for manipulating files."""

import os
from datetime import datetime

from django import template

register = template.Library()


@register.filter
def get_file_type(queryset, key):
    """Returns the first file in a queryset with a given file type."""
    return queryset.filter(type=key).first()


@register.simple_tag(takes_context=True)
def file_last_modified(context, filename=None, date_format="%d %B %Y"):
    """
    Returns the last modified date of a given file or the current template.

    Args:
        context (dict): Template context.
        filename (str, optional): Path of file to check (default: current template).
        date_format (str): Date format (default: "%d %B %Y").

    Returns:
        str: Last modified date of the file (or "Unknown" if file is not found).
    """
    if filename is None:
        # Get current file
        template_name = context.template_name
        filename = template.loader.get_template(template_name).origin.name

    try:
        timestamp = os.path.getmtime(filename)
        return datetime.fromtimestamp(timestamp).strftime(date_format)
    except FileNotFoundError:
        return "Unknown"
