"""Utilities to render Markdown files as HTML."""

from django.utils.text import slugify

import os
import frontmatter

import mistune
from mistune.directives import (
    RSTDirective,
    FencedDirective,
    Admonition,
    TableOfContents,
)
from mistune.toc import add_toc_hook, render_toc_ul

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html, HtmlFormatter
from pygments.util import ClassNotFound

from ..templatetags.bca_website_links import github_url


class CustomTOC(TableOfContents):
    """Create Table of Contents with custom identifiers."""

    @staticmethod
    def create_heading_id(text):
        """Create custom heading ID."""
        return slugify(text)

    @staticmethod
    def generate_toc_heading_id(token, index):
        """Generate custom heading ID for Table of Contents."""
        return CustomTOC.create_heading_id(token["text"])

    def generate_heading_id(self, token, index):
        """Custom heading ID generator."""
        return self.generate_toc_heading_id(token, index)


class MarkdownRenderer(mistune.HTMLRenderer):
    """Custom Markdown renderer."""

    def __init__(self, static_dir=None, *args, **kwargs):
        """Add static directory for media."""
        super().__init__(*args, **kwargs)
        self.static_dir = static_dir

    def image(self, alt="", url="", title=None):
        """Fix path to image and make it responsive."""

        # Add static dir in relative URLs
        if self.static_dir and not url.startswith(("http://", "https://", "/")):
            url = os.path.join(self.static_dir, url)

        # Make image responsive
        attrs = f' src="{url}" alt="{alt}" class="img-fluid"'
        if title:
            attrs += f' title="{title}"'
        return f"<img{attrs}>"

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

        tag = f"h{level}"
        class_attr = f"class='h{level + 2}''"

        # Prepare heading ID
        _id = CustomTOC.create_heading_id(text)
        id_attr = f"id='{_id}'" if _id is not None else None

        return f"<{tag} {class_attr} {id_attr}>{text}</{tag}>\n"


class MarkdownPage:
    """Create HTML page from Markdown content."""

    def __init__(self, filename, static_dir=None, parser=None):
        """Initialize Markdown file parsing."""
        self.filename = filename
        self.static_dir = static_dir
        self._parser = parser
        self._html = None
        self._toc = None

        # Load metadata and Markdown content from filename
        self.content = None
        self.metadata = None
        self.prepare_content()

    def prepare_content(self):
        """Prepare file content and metadata based on frontmatter."""
        post = frontmatter.load(self.filename)
        self.metadata = post.metadata
        self.content = post.content

    @property
    def parser(self):
        """Prepare Markdown parser with plugins."""
        if self._parser:
            return self._parser

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
        self._parser = mistune.create_markdown(renderer=MarkdownRenderer(static_dir=self.static_dir), plugins=plugins)
        return self._parser

    @property
    def html(self):
        """Parse Markdown content in HTML format."""
        if self._html:
            return self._html

        self._html = self.parser(self.content)
        return self._html

    @property
    def toc(self):
        """Parse table of contents in HTML format."""
        if self._toc:
            return self._toc

        md = self.parser
        add_toc_hook(md, heading_id=CustomTOC.generate_toc_heading_id)

        html, state = md.parse(self.content)
        toc_items = state.env["toc_items"]
        self._toc = render_toc_ul(toc_items)
        return self._toc

    def get_pygment_css(self, arg=".highlight"):
        """Get CSS style definitions from pygments."""
        return HtmlFormatter().get_style_defs(arg)

    def get_action_links(self, path=None, branch="main"):
        """Get URL for multiple actions regarding the selected Markdown page."""
        path = path or self.filename
        action_links = {
            "github": github_url(f"blob/{branch}/{path}"),
            "edit": github_url(f"edit/{branch}/{path}"),
            "history": github_url(f"commits/{branch}/{path}"),
            "feedback": github_url(f"edit/{branch}/{path}"),
        }
        return action_links
