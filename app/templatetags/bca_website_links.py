"""
Django template tags for generating links to a BCA website page.
"""

from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def bca_url(param=None):
    domain = getattr(settings, 'BCA_WEBSITE')
    param = param or ''
    return f"{domain.rstrip('/')}/{param}"
