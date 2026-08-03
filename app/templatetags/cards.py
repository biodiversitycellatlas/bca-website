"""
Django template tags for generating download links and download cards.
"""

import random
from urllib.parse import urlparse, urlunparse

from django import template

register = template.Library()


def _optimise_img_url(**kwargs):
    """Optimise URL query parameters depending on image source."""

    img_url = kwargs.get("img_url")
    img_source = None
    if img_url and "unsplash" in img_url.lower():
        params = {
            "crop": "entropy",
            "cs": "tinysrgb",
            "fit": "max",
            "fm": "webp",
            "q": "80",
            "w": "800",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        parsed = urlparse(img_url)
        img_url = urlunparse(parsed._replace(query=query))
        img_source = "Unsplash"

    return {**kwargs, "img_url": img_url, "img_source": img_source}


def _build_card_context(title, description, **kwargs):
    """
    Build card context with optional optimized Unsplash image.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        **kwargs:
            - img_url (str, optional): Image URL to display.
            - img_author (str, optional): Image author name.
            - img_author_handle (str, optional): Image author social handle.
            - img_width (int or str, optional): Image width.

    Returns:
        str: rendered HTML with download card.
    """
    img = _optimise_img_url(**kwargs)
    return {"title": title, "description": description, **kwargs, **img}


@register.inclusion_tag("app/components/cards/card.html")
def card(title, description=None, links=None, visible_count=None, collapsed_label=None, **kwargs):
    """
    Render a card with information.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        links (str): List of links displayed on card.
        visible_count (int, optional): Number of links to show before collapsing the rest.
        collapsed_label (str, optional): Label of the collapse toggle.
        **kwargs (optional): Image arguments (see `_build_card_context`).

    Returns:
        str: rendered HTML with download card.
    """
    if links is not None:
        kwargs["links"] = links

    if visible_count is not None:
        kwargs["visible_items"] = links[:visible_count]
        kwargs["collapsed_items"] = links[visible_count:]

    if kwargs.get("collapsed_items"):
        kwargs["collapse_id"] = f"collapsed-items-{random.getrandbits(8)}"
        kwargs["collapsed_label"] = collapsed_label or "View all"
    return _build_card_context(title, description, **kwargs)


@register.inclusion_tag("app/components/cards/download_card.html")
def download_card(title, description, view, filename, **kwargs):
    """
    Render a card containing downloadable links.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        view (str): View name to generate URLs.
        filename (str): Filename for download.
        **kwargs (optional): Image arguments (see `_build_card_context`).

    Returns:
        str: rendered HTML with card with downloadable data.
    """
    kwargs["view"] = view
    kwargs["filename"] = filename
    return _build_card_context(title, description, **kwargs)


@register.inclusion_tag("app/components/cards/qc_card.html")
def qc_card(title, description, metrics, **kwargs):
    """
    Render a card with quality control information.

    Args:
        title (str): Title displayed on card.
        description (str): Description displayed on card.
        metrics (list): Quality control metrics.
        **kwargs (optional): Image arguments (see `_build_card_context`).

    Returns:
        str: rendered HTML with card.
    """
    kwargs["metrics"] = metrics
    return _build_card_context(title, description, **kwargs)


@register.inclusion_tag("app/components/cards/news_card.html")
def news_card(title, date, link, **kwargs):
    """
    Render a news card.

    Args:
        title (str): Title displayed on card.
        date (str): Date of publication.
        link (str): Link to post.
        **kwargs (optional): Image arguments (see `_build_card_context`).

    Returns:
        str: rendered HTML with card.
    """
    kwargs["date"] = date
    kwargs["link"] = link
    return _build_card_context(title, None, **kwargs)
