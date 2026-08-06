"""
Django template tags emitting Bioschemas JSON-LD blocks.

Each tag renders one ``<script type="application/ld+json">`` element into the
``structured_data`` block of `base.html`. The payloads themselves are built by
`app.utils.bioschemas`; this module only handles serialisation and escaping.

Usage::

    {% block structured_data %}
        {% load bioschemas %}
        {% bioschemas_taxon species %}
    {% endblock structured_data %}
"""

import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe

from ..utils import bioschemas

register = template.Library()

# Only these three characters need escaping inside a script element; HTML entity
# escaping would break JSON parsing, so `simple_tag` + mark_safe is used rather
# than an inclusion tag (which would re-enter the template engine and re-escape).
_ESCAPES = {
    ord("<"): "\\u003C",
    ord(">"): "\\u003E",
    ord("&"): "\\u0026",
}


def _script(payload):
    """Serialise a top-level JSON-LD node into a script element."""
    if not payload:
        return ""

    body = json.dumps(
        bioschemas.as_root(payload),
        cls=DjangoJSONEncoder,
        indent=2,
        ensure_ascii=False,
    ).translate(_ESCAPES)

    # nosec justification: `body` is JSON-serialised output, so every string is
    # already quote- and backslash-escaped, and `_ESCAPES` unicode-escapes the only
    # characters that could terminate the element. It therefore cannot break out of
    # the script context -- the same argument Django makes for `html.json_script`.
    # `test_script_escapes_html_sensitive_characters` pins this behaviour.
    return mark_safe(  # nosec B308, B703
        f'<script type="application/ld+json">\n{body}\n</script>'
    )


def _request(context):
    """Return the request from the template context, if available."""
    return context.get("request")


def _missing(obj):
    """
    Return True when there is no model instance to describe.

    Unresolved template variables arrive as `string_if_invalid` (an empty string
    by default), and the Cell Atlas views deliberately put a string in `gene` /
    `dataset` when the requested entity does not exist.
    """
    return not obj or isinstance(obj, str)


@register.simple_tag(takes_context=True)
def bioschemas_taxon(context, species):
    """Render a Bioschemas Taxon block for a species."""
    if _missing(species):
        return ""
    return _script(bioschemas.taxon(species, _request(context)))


@register.simple_tag(takes_context=True)
def bioschemas_gene(context, gene):
    """Render a Bioschemas Gene block for a gene."""
    if _missing(gene):
        return ""
    return _script(bioschemas.gene(gene, _request(context)))


@register.simple_tag(takes_context=True)
def bioschemas_dataset(context, dataset):
    """Render a Bioschemas Dataset block for a dataset."""
    if _missing(dataset):
        return ""
    return _script(bioschemas.dataset(dataset, _request(context)))


@register.simple_tag(takes_context=True)
def bioschemas_data_catalog(context, datasets=None, name=None, description=None):
    """Render a Bioschemas DataCatalog block, optionally listing datasets."""
    return _script(
        bioschemas.data_catalog(
            _request(context),
            name=name,
            description=description,
            datasets=datasets,
        )
    )


@register.simple_tag(takes_context=True)
def bioschemas_download_catalog(context, species=None, datasets=None, name=None, description=None):
    """Render a DataCatalog block listing the downloadable files and datasets."""
    request = _request(context)
    return _script(
        bioschemas.data_catalog(
            request,
            name=name,
            description=description,
            datasets=datasets,
            distributions=bioschemas.species_file_distributions(request, species),
        )
    )


@register.simple_tag(takes_context=True)
def bioschemas_species_list(context, species_list, name=None):
    """Render a CollectionPage listing Taxon stubs for the species on the page."""
    if not species_list:
        return ""
    return _script(
        bioschemas.item_list(
            species_list,
            _request(context),
            builder=lambda obj, request: bioschemas.taxon(obj, request, minimal=True),
            name=name,
        )
    )


@register.simple_tag(takes_context=True)
def bioschemas_gene_list(context, genes, name=None):
    """Render a CollectionPage listing Gene stubs for the genes on the page."""
    if not genes:
        return ""
    return _script(
        bioschemas.item_list(
            genes,
            _request(context),
            builder=lambda obj, request: bioschemas.gene(obj, request, minimal=True),
            name=name,
        )
    )
