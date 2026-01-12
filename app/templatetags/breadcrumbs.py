"""Sticky navigation bar with breadcrumbs."""

from django import template

register = template.Library()


@register.inclusion_tag("app/components/links/breadcrumbs.html", takes_context=True)
def breadcrumbs(context, root=None, css_class=""):
    """Generate breadcrumb links from the current request path."""

    request = context["request"]
    path = request.path.strip("/").split("/")
    crumbs = []
    url = ""

    for i, segment in enumerate(path):
        url += f"/{segment}"

        if root is not None and i == 0:
            label = root
        elif segment in ["gene-module", "gene-list"]:
            label = segment.replace("-", " ").capitalize()
        elif segment == segment.lower():
            # Capitalize if label is in lowercase
            label = segment.capitalize()
        else:
            label = segment
        crumbs.append((label, url))

    return {
        "crumbs": crumbs,
        "css_class": css_class
    }
