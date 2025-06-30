from django import template

register = template.Library()

def _build_download_context(viewname, slug, prefix, is_detail):
    return {
        'viewname': viewname,
        'slug': slug,
        'prefix': prefix,
        'formats': ['csv', 'tsv', 'json'],
        'is_detail': is_detail,
    }

@register.inclusion_tag('app/components/links/download_dataset_links.html')
def download_dataset_list(viewname, slug, prefix):
    return _build_download_context(viewname, slug, prefix, is_detail=False)

@register.inclusion_tag('app/components/links/download_dataset_links.html')
def download_dataset_detail(viewname, slug, prefix):
    return _build_download_context(viewname, slug, prefix, is_detail=True)
