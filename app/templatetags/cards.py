"""
Django template tags for generating download links and download cards.
"""

from urllib.parse import urlparse, urlunparse

from django import template

register = template.Library()


def _build_card_context(
    title,
    description,
    links=None,
    img_url=None,
    img_author=None,
    img_author_handle=None,
    img_width=None,
    metrics=None
):
    """
    Build card context with optional optimized Unsplash image.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        links (list, optional): List of links displayed on card.
        img_url (str, optional): Image URL to display.
        img_author (str, optional): Image author name.
        img_author_handle (str, optional): Image author social handle.
        img_width (int): Image width.
        metrics (list, optional): Quality control metrics.

    Returns:
        str: rendered HTML with download card.
    """
    img_source = None
    if img_url and "unsplash" in img_url.lower():
        # Optimise Unsplash images
        params = {
            "crop": "entropy",
            "cs": "tinysrgb",
            "fit": "max",
            "fm": "webp",
            "q": "80",
            "w": "400",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        parsed = urlparse(img_url)
        img_url = urlunparse(parsed._replace(query=query))
        img_source = "Unsplash"

    return {
        "title": title,
        "description": description,
        "links": links,
        "img_url": img_url,
        "img_author": img_author,
        "img_author_handle": img_author_handle,
        "img_source": img_source,
        "img_width": img_width,
        "metrics": metrics,
    }


@register.inclusion_tag("app/components/links/card.html")
def card(
    title,
    description,
    links=None,
    img_url=None,
    img_author=None,
    img_author_handle=None,
    img_width=None,
):
    """
    Render a card with information.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        links (str, optional): List of links displayed on card.
        img_url (str, optional): Image URL to display.
        img_author (str, optional): Image author name.
        img_author_handle (str, optional): Image author social handle.
        img_width (int): Image width.

    Returns:
        str: rendered HTML with download card.
    """
    return _build_card_context(
        title, description, links, img_url, img_author, img_author_handle, img_width, metrics=None
    )


@register.inclusion_tag("app/components/links/links_list.html")
def links_list(items):
    return {"items": items}


@register.inclusion_tag("app/components/cards/qc_card.html")
def qc_card(
    title,
    description,
    img_url=None,
    img_author=None,
    img_author_handle=None,
    img_width=None,
    metrics=None,
):
    """
    Render a card with information.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        metrics (list, optional): List of quality control metrics displayed on card.
        img_url (str, optional): Image URL to display.
        img_author (str, optional): Image author name.
        img_author_handle (str, optional): Image author social handle.

    Returns:
        str: rendered HTML with card.
    """
    return _build_card_context(
        title, description, metrics=metrics,
        img_url=img_url, img_author=img_author, img_author_handle=img_author_handle
    )
