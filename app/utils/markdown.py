from django.utils.text import slugify

import mistune
from mistune.directives import (
    RSTDirective,
    FencedDirective,
    Admonition,
    TableOfContents,
)

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html, HtmlFormatter
from pygments.util import ClassNotFound


class MarkdownRenderer(mistune.HTMLRenderer):
    """Custom Markdown renderer."""

    def block_code(self, code, info=None):
        """Add syntax highlight in code blocks."""

        block = "<pre><code>" + mistune.escape(code) + "</code></pre>"
        if info:
            try:
                lexer = get_lexer_by_name(info, stripall=True)
                formatter = html.HtmlFormatter()
                block = highlight(code, lexer, formatter)
            except ClassNotFound:
                pass
        return block

    def heading(self, text, level, **attrs):
        """Customise headings to standardize appearance."""

        tag = "h{level}"
        class_attr = f"class='h{level + 2}''"

        _id = attrs.get("id")
        id_attr = f"id='{_id}'" if _id is not None else None

        return f"<{tag} {class_attr} {id_attr}>{text}</{tag}>\n"


class CustomTOC(TableOfContents):
    """Table of Contents with custom identifiers."""

    def generate_heading_id(self, token, index):
        """Custom heading ID generator."""
        return slugify(token["text"])


def render_markdown(content):
    """Render Markdown content."""

    plugins = [
        "table",
        "strikethrough",
        "footnotes",
        "url",
        "task_lists",
        "def_list",
        "abbr",
        "mark",
        "insert",
        "superscript",
        "subscript",
        "math",
        "spoiler",
        FencedDirective([Admonition()]),
        RSTDirective([CustomTOC()]),
    ]
    markdown = mistune.create_markdown(renderer=MarkdownRenderer(), plugins=plugins)
    return markdown(content)


def get_pygments_css(arg=".highlight"):
    """Get CSS style definitions from pygments."""

    return HtmlFormatter().get_style_defs(arg)
