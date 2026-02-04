from django import template

register = template.Library()


@register.inclusion_tag("app/components/buttons/data_download.html")
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
    return {"id": id}


@register.inclusion_tag("app/components/buttons/copy_to_clipboard.html", takes_context=True)
def clipboard_button(context, id="", text=""):
    """
    Button to copy current URL (optionally with hash #id) to clipboard.

    Inputs:
    - id (optional): suffix for element ID and hash anchor
    - text (optional): button label (default icon + "Copy link")
    """
    return {
        "id": id,
        "text": text,
    }


def _render_heading(context, title, id=None, tag="h1", clipboard_button=True, data_dropdown=True):
    """
    Heading to show copy link and data dropdown buttons

    Inputs:
    - title: heading title
    - id: title identifier (used as anchor)
    - tag: heading tag (default: 'h1')
    - clipboard_button: show 'copy link' button (default: True)
    - data_dropdown: show 'data' dropwdown button (default: True)
    """

    if tag == "h1":
        h_class = "h3"
    elif tag == "h2":
        h_class = "h4"
    else:
        h_class = "h5"

    return {
        "title": title,
        "id": id,
        "tag": tag,
        "h_class": h_class,
        "clipboard_button": clipboard_button,
        "data_dropdown": data_dropdown,
    }


@register.inclusion_tag("app/components/heading.html", takes_context=True)
def h1(context, title, id=None, clipboard_button=True, data_dropdown=True):
    return _render_heading(context, title, id, "h1", clipboard_button, data_dropdown)


@register.inclusion_tag("app/components/heading.html", takes_context=True)
def h2(context, title, id=None, clipboard_button=True, data_dropdown=True):
    return _render_heading(context, title, id, "h2", clipboard_button, data_dropdown)
