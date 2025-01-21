from django import template
from django.template.defaultfilters import stringfilter
from datetime import datetime
import os

register = template.Library()

@register.simple_tag
def file_last_modified(file_path, format_string="%d %B %Y"):
    """
    Returns the last modified date of a file.
    """
    try:
        timestamp = os.path.getmtime(file_path)
        return datetime.fromtimestamp(timestamp).strftime(format_string)
    except FileNotFoundError:
        return None

@register.simple_tag
def startswith(value, arg):
    return value.startswith(arg)
