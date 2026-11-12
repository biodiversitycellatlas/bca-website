"""
Utilities for parsing Newick-format phylogenetic trees.
"""


def parse_newick_labels(newick: str) -> set[str]:
    """
    Extract all node labels from a Newick string.

    Args:
        newick: Newick-formatted tree string.

    Returns:
        Set of node labels (empty labels are omitted).

    Raises:
        ValueError: If the Newick string is malformed.
    """
    parser = _NewickParser(newick)
    parser.parse_tree()
    parser.expect_end()
    return parser.labels


class _NewickParser:
    """Recursive-descent parser for Newick node labels."""

    def __init__(self, newick: str):
        self.newick = newick
        self.pos = 0
        self.labels: set[str] = set()

    def parse_tree(self):
        """Parse a single tree (clade or lone labeled node)."""
        self._skip_insignificant()
        if self._peek() == "(":
            self._parse_clade()
        else:
            self._parse_label()

    def _parse_clade(self):
        self._expect("(")
        self.parse_tree()
        while True:
            self._skip_insignificant()
            if self._peek() != ",":
                break
            self._advance()
            self.parse_tree()
        self._expect(")")
        self._parse_label()
        self._parse_branch()

    def _parse_label(self):
        self._skip_insignificant()
        if self._peek() == '"':
            label = self._parse_quoted()
        else:
            label = self._parse_unquoted()
        if label:
            self.labels.add(label)
        self._parse_branch()

    def _parse_quoted(self) -> str:
        self._expect('"')
        start = self.pos
        while self.pos < len(self.newick) and self.newick[self.pos] != '"':
            if self.newick[self.pos] == "\\":
                self.pos += 1  # skip escaped character
            self.pos += 1
        if self.pos >= len(self.newick):
            raise ValueError("Unterminated quoted label in Newick string.")
        label = self.newick[start : self.pos]
        self._expect('"')
        return label

    def _parse_unquoted(self) -> str:
        start = self.pos
        while self.pos < len(self.newick) and self.newick[self.pos] not in '()":;,[':
            self.pos += 1
        return self.newick[start : self.pos]

    def _parse_branch(self):
        self._skip_insignificant()
        if self._peek() == ":":
            self._advance()
            while self.pos < len(self.newick) and self.newick[self.pos] not in '()":;,[':
                self.pos += 1

    def _skip_insignificant(self):
        """Skip whitespace and [ ... ] comments."""
        while self.pos < len(self.newick):
            ch = self.newick[self.pos]
            if ch.isspace():
                self.pos += 1
            elif ch == "[":
                end = self.newick.find("]", self.pos)
                if end == -1:
                    raise ValueError("Unterminated comment in Newick string.")
                self.pos = end + 1
            else:
                break

    def _peek(self) -> str:
        return self.newick[self.pos] if self.pos < len(self.newick) else ""

    def _advance(self):
        self.pos += 1

    def _expect(self, ch: str):
        if self._peek() != ch:
            raise ValueError(f"Expected {ch!r} at position {self.pos} in Newick string.")
        self._advance()

    def expect_end(self):
        """Consume the terminating semicolon and reject trailing content."""
        self._skip_insignificant()
        if self._peek() == ";":
            self._advance()
        self._skip_insignificant()
        if self.pos != len(self.newick):
            raise ValueError(f"Trailing content at position {self.pos} in Newick string.")
