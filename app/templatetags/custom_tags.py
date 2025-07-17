from django import template
from datetime import datetime
import os

register = template.Library()


@register.simple_tag(takes_context=True)
def file_last_modified(context, filename=None, format="%d %B %Y"):
    """
    Returns the last modified date of a given file or the current template.

    Args:
        context (dict): Template context.
        filename (str, optional): Path of file to check (default: current template).
        format (str): Timestamp format (default: "%d %B %Y").

    Returns:
        str: Last modified date of the file (or "Unknown" if file is not found).
    """
    if filename is None:
        # Get current file
        template_name = context.template_name
        filename = template.loader.get_template(template_name).origin.name

    try:
        timestamp = os.path.getmtime(filename)
        return datetime.fromtimestamp(timestamp).strftime(format)
    except FileNotFoundError:
        return "Unknown"


@register.simple_tag
def startswith(value, arg):
    """Returns true if the value starts with a given string."""
    return value.startswith(arg)
