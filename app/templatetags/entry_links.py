"""
Template tags to generate HTML links and header counters for entry pages.
"""

from django import template

register = template.Library()


@register.simple_tag
def dataset_gene_link(dataset, gene):
    """
    Return HTML link for a gene within a dataset.

    Args:
        dataset: Dataset object.
        gene: Gene object.

    Returns:
        str: HTML link to the gene within the dataset context.
    """
    url = dataset.get_gene_url(gene=gene.name)
    return dataset.get_html_link(url=url)


@register.simple_tag
def species_genelist_link(species, genelist):
    """
    Return HTML link for a gene list within a species.

    Args:
        species: Species object.
        genelist: GeneList object.

    Returns:
        str: HTML link to the genelist page for the species.
    """
    url = species.get_genelist_list_url(genelist=genelist.name)
    return species.get_html_link(url=url, show_common_name=True)


@register.simple_tag
def species_domain_link(species, domain):
    """
    Return HTML link for a domain within a species.

    Args:
        species: Species object.
        domain (str): Protein domain.

    Returns:
        str: HTML link to the domain page for the species.
    """
    url = species.get_domain_list_url(domain=domain)
    return species.get_html_link(url=url, show_common_name=True)


@register.simple_tag
def get_genelist_link_by_species(genelist, species):
    """
    Return HTML link for a GeneList page filtered by species.

    Args:
        genelist: Genelist object.
        species: Species object.

    Returns:
        str: HTML link to the genelist within the species context.
    """
    url = species.get_genelist_list_url(genelist=genelist.name)
    return genelist.get_html_link(url=url)


@register.inclusion_tag("app/components/entry_header_count.html")
def render_header_counter(title, paginator, obj=None):
    """
    Render reusable header counter component.

    Args:
        title (str): Header title.
        paginator: Paginator object.
        obj (optional): Extra argument with object.

    Returns:
        dict: Context for rendering the header counter template.
    """
    return {
        "title": title,
        "object": obj,
        "paginator": paginator,
    }
