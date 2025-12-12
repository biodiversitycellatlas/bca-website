"""Sticky navigation bar with breadcrumbs."""

from django import template

register = template.Library()


@register.inclusion_tag("app/components/links/breadcrumbs.html", takes_context=True)
def breadcrumbs(context, main_label=None):
    """Generate breadcrumb links from the current request path."""

    request = context["request"]
    path = request.path.strip("/").split("/")
    crumbs = []
    url = ""

    for i, segment in enumerate(path):
        url += f"/{segment}"

        if main_label is not None and i == 0:
            label = main_label
        elif segment in ["gene-module", "gene-list"]:
            label = segment.replace("-", " ").capitalize()
        elif segment == segment.lower():
            # Capitalize if label is all in lowercase
            label = segment.capitalize()
        else:
            label = segment
        crumbs.append((label, url))

    return {"crumbs": crumbs}
