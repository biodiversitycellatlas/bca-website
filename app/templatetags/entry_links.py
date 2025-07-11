from django import template
from django.utils.safestring import mark_safe

from ..models import Ortholog

register = template.Library()

@register.simple_tag
def dataset_gene_link(dataset, gene):
    url = dataset.get_gene_url(gene=gene.name)
    return dataset.get_html_link(url=url)

@register.simple_tag
def species_genelist_link(species, genelist):
    url = species.get_genelist_list_url(genelist=genelist.name)
    return species.get_html_link(url=url)

@register.inclusion_tag('app/components/entry_header_count.html')
def render_header_counter(title, paginator, object=None):
    return {
    	'title': title,
        'object': object,
        'paginator': paginator,
    }
