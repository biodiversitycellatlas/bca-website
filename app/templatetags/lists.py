"""
Django template tags for generating download links and download cards.
"""

from django import template


register = template.Library()


def _build_list_context(title, link, category, **kwargs):
    """
    Build card context with optional optimized Unsplash image.

    Args:
        title (str): Title.
        link (str): URL link.
        category (str): Category.
        **kwargs:
            - date (str, optional): Date.
            - journal (str, optional): Journal.
            - location (str, optional): Location.
            - duration (str, optional): Duration.
            - type (str, optional): Type of content.

    Returns:
        str: rendered HTML with download card.
    """
    return {"title": title, "link": link, "category": category, **kwargs}


@register.inclusion_tag("app/components/lists/news_list.html")
def news_list(title, link, category, **kwargs):
    """
    Render list of news.

    Args:
        title (str): Title.
        link (str): URL link.
        **kwargs: optional elements (see _build_list_context).

    Returns:
        str: rendered HTML with download links.
    """
    return _build_list_context(title, link, category, **kwargs)
