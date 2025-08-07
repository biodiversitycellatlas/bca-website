from django import template
from django.urls import resolve
from django.utils.safestring import mark_safe

register = template.Library()


@register.inclusion_tag("app/components/links/breadcrumbs.html", takes_context=True)
def breadcrumbs(context):
    request = context["request"]
    path = request.path.strip("/").split("/")
    crumbs = []
    url = ""

    for i, segment in enumerate(path):
        url += f"/{segment}"
        if segment == "entry":
            label = "BCA database entries"
        elif segment in ["gene-module", "gene-list"]:
            label = segment.replace("-", " ").capitalize()
        elif not any(c.isupper() for c in segment):
            label = segment.capitalize()
        else:
            label = segment
        crumbs.append((label, url))

    return {"crumbs": crumbs}
