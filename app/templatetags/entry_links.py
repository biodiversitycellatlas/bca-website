from django import template
from django.utils.safestring import mark_safe

from ..models import Ortholog

register = template.Library()

@register.simple_tag
def dataset_gene_link(dataset, gene):
    url = dataset.get_gene_url(gene=gene.name)
    return dataset.get_html_link(url=url)
