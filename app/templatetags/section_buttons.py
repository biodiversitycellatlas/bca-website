from django import template

register = template.Library()


@register.inclusion_tag('app/components/button/data_download.html')
def data_dropdown(id):
    """
    Dropdown button to view and download data

    Features:
    - Displays buttons for viewing, downloading and copying API links for
      multiple data types
    - Output format selection: CSV, TSV, JSON
    - Selected output format is saved to local storage and loaded at page load

    Input:
    - id: suffix to create unique identifiers to all elements
    """
    return {'id': id}


@register.inclusion_tag('app/components/button/copy_to_clipboard.html', takes_context=True)
def clipboard_button(context, id='', text=''):
    """
    Button to copy current URL (optionally with hash #id) to clipboard.

    Inputs:
    - id (optional): suffix for element ID and hash anchor
    - text (optional): button label (default icon + "Copy link")
    """
    return {
        'id': id,
        'text': text,
    }
