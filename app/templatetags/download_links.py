from django import template

register = template.Library()

def _build_download_context(viewname, slug, suffix, is_detail):
    return {
        'viewname': viewname,
        'slug': slug,
        'suffix': suffix,
        'formats': ['csv', 'tsv', 'json'],
        'is_detail': is_detail,
    }

@register.inclusion_tag('app/components/links/download_dataset_links.html')
def download_dataset_list(viewname, slug, suffix):
    return _build_download_context(viewname, slug, suffix, is_detail=False)

@register.inclusion_tag('app/components/links/download_dataset_links.html')
def download_dataset_detail(viewname, slug, suffix):
    return _build_download_context(viewname, slug, suffix, is_detail=True)
