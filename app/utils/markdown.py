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

        # Alwa
        _id = CustomTOC.create_heading_id(text)
        id_attr = f"id='{_id}'" if _id is not None else None

        return f"<{tag} {class_attr} {id_attr}>{text}</{tag}>\n"


class MarkdownPage():
    """Create HTML page from Markdown content."""

    def __init__(self, filename):
        """Initialize Markdown file parsing."""
        self.filename = filename
        self.content = None
        self.html = None
        self.toc = None
        self.metadata = None
        self.parser = None
        self.css = None

        # Load code block syntax highlighting
        self.css = self.prepare_pygments_css()

        # Read file
        md = None
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                self.prepare_parser()
                self.prepare_content()
                self.parse_html()
                self.parse_toc_html()

    def get_html(self):
        """Get Markdown content in HTML format."""
        return self.html

    def get_css(self):
        """Get CSS styles for Markdown content."""
        return self.css

    def get_toc(self):
        """Get Table of Contents in HTML format."""
        return self.toc

    def get_metadata(self):
        return self.metadata

    def prepare_parser(self):
        """Prepare Markdown parser with plugins."""

        if self.parser:
           return self.parser

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
        self.parser = mistune.create_markdown(renderer=MarkdownRenderer(), plugins=plugins)
        return self.parser

    def prepare_content(self):
        """Prepare file content and metadata based on frontmatter."""
        post = frontmatter.load(self.filename)
        self.metadata = post.metadata
        self.content = post.content

    def parse_html(self):
        """Parse Markdown content in HTML format."""
        if self.html:
            return self.html

        self.html = self.parser(self.content)
        return self.html

    def parse_toc_html(self):
        """Parse table of contents in HTML format."""
        if self.toc:
            return self.toc

        md = self.parser
        add_toc_hook(md, heading_id=CustomTOC.generate_toc_heading_id)

        html, state = md.parse(self.content)
        toc_items = state.env['toc_items']
        self.toc = render_toc_ul(toc_items)
        return self.toc

    def prepare_pygments_css(self, arg=".highlight"):
        """Get CSS style definitions from pygments."""
        if self.css:
            return self.css

        self.css = HtmlFormatter().get_style_defs(arg)
        return self.css

    def __repr__(self):
        """String representation of parsed Markdown file in HTML."""
        return self.content
