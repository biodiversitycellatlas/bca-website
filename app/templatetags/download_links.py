from django import template
from urllib.parse import urlparse, urlunparse

register = template.Library()

def _build_download_context(view, suffix, slug=None, type='button'):
    return {
        'view': view,
        'slug': slug,
        'suffix': suffix,
        'formats': ['csv', 'tsv', 'json'],
        'type': type,
    }

@register.inclusion_tag('app/components/links/download_links.html')
def download_dataset_data(view, suffix, slug, type='link'):
    return _build_download_context(view, suffix, slug, type)

@register.inclusion_tag('app/components/links/download_links.html')
def download_info(view, suffix, type='link'):
    return _build_download_context(view, suffix, None, type)

@register.inclusion_tag('app/components/links/download_card.html')
def download_card(view, filename, title, description, img_url=None, img_author=None, img_author_handle=None):
    img_source = None
    if img_url and 'unsplash' in img_url.lower():
        # Optimise Unsplash images
        params = {
            'crop': 'entropy',
            'cs': 'tinysrgb',
            'fit': 'max',
            'fm': 'webp',
            'q': '80',
            'w': '400'
        }

        query = '&'.join(f'{k}={v}' for k, v in params.items())
        parsed = urlparse(img_url)
        img_url = urlunparse(parsed._replace(query=query))
        img_source = 'Unsplash'

    return {
        'view': view,
        'filename': filename,
        'title': title,
        'description': description,
        'img_url': img_url,
        'img_author': img_author,
        'img_author_handle': img_author_handle,
        'img_source': img_source
    }