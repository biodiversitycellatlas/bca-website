"""
Django template tags for generating download links and download cards.
"""

from django import template


register = template.Library()


def _build_download_context(
    view, suffix, slug=None, render="link", formats=("csv", "tsv", "json")
):
    """
    Build context dictionary for download links in multiple formats.

    Args:
        view (str): View name to generate URLs.
        suffix (str): Suffix for filename.
        slug (str, optional): Dataset or species slug.
        formats (list, optional): List of available download formats
            (default: ['csv', 'tsv', 'json']).
        render (str, optional): Render as 'link' or 'button' (default: 'link').

    Returns:
        dict: Context data.
    """
    return {
        "view": view,
        "slug": slug,
        "suffix": suffix,
        "formats": formats,
        "type": render,
    }


@register.inclusion_tag("app/components/links/download_links.html")
def download_dataset_data(view, suffix, slug, render="link"):
    """
    Render download links for dataset data in multiple formats.

    Args:
        view (str): View name to generate URLs.
        suffix (str): Suffix for filename.
        slug (str): Dataset slug.
        render (str, optional): Render as 'link' or 'button' (default: 'link').

    Returns:
        str: rendered HTML with download links.
    """
    return _build_download_context(view, suffix, slug, render)


@register.inclusion_tag("app/components/links/download_links.html")
def download_info(view, suffix, render="link"):
    """
    Render download links for species or dataset information.

    Args:
        view (str): View name to generate URLs.
        suffix (str): Suffix for filename.
        render (str, optional): Render as 'link' or 'button' (default: 'link').

    Returns:
        str: rendered HTML with download links.
    """
    return _build_download_context(view, suffix, render=render)
