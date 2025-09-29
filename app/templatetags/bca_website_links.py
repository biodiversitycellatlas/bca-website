"""
Django template tags for generating links to a BCA website page.
"""

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def bca_url(path=None):
    """Return URL to BCA main website with path as suffix."""
    domain = getattr(settings, "BCA_WEBSITE", "http://biodiversitycellatlas.org")
    path = path or ""
    return f"{domain.rstrip('/')}/{path}"


@register.simple_tag
def github_url(path=None):
    """Return URL to GitHub repository with path as suffix."""
    domain = getattr(
        settings, "GITHUB_URL", "https://github.com/biodiversitycellatlas/bca-website"
    )
    path = path or ""
    return f"{domain.rstrip('/')}/{path}"


@register.simple_tag
def github_release_url(path=None):
    """Return URL to GitHub repository with path as suffix."""
    domain = getattr(
        settings, "GITHUB_URL", "https://github.com/biodiversitycellatlas/bca-website"
    )
    tag = getattr(settings, "GIT_VERSION")

    if tag is None:
        return github_url(path)

    path = path or ""
    return f"{domain.rstrip('/')}/releases/tag/{tag}/{path}"
