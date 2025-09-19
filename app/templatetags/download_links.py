"""
Django template tags for generating download links and download cards.
"""

from django import template

from .cards import _build_card_context

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
    return _build_download_context(view, suffix, None, render)


@register.inclusion_tag("app/components/links/download_card.html")
def download_card(
    view,
    filename,
    title,
    description,
    links=None,
    img_url=None,
    img_author=None,
    img_author_handle=None,
    img_width=None,
):
    """
    Render a card containing downloadable links.

    Args:
        view (str): View name to generate URLs.
        filename (str): Filename for download.
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        links (str, optional): List of links displayed on card.
        img_url (str, optional): Image URL to display.
        img_author (str, optional): Image author name.
        img_author_handle (str, optional): Image author social handle.
        img_width (int): Image width.

    Returns:
        str: rendered HTML with card with downloadable data.
    """
    context = _build_card_context(
        title, description, links, img_url, img_author, img_author_handle, img_width
    )
    context.update({"view": view, "filename": filename})
    return context
