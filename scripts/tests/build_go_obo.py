#!/usr/bin/env python3
"""
Download and build a filtered GO basic OBO file for testing.

Usage:
    import build_go_obo
    builder = GeneOntologyOboBuilder()
    builder.prepare_filtered_go_obo()
"""

from pathlib import Path
import gzip
import re
import requests

from goatools.obo_parser import GODag


class GeneOntologyOboBuilder:
    """Build a filtered GO basic OBO file for testing."""

    def __init__(self, obo_url="https://purl.obolibrary.org/obo/go/go-basic.obo" base_dir=None, emapper_file=None, obo_file=None, obo_subset_file=None, output_file=None, skip_prefixes=None):
        self.base_dir = base_dir or Path(__file__).parent / "test_fixtures"
        self.emapper_file = emapper_file or self.base_dir / "emapper_annotation.txt.gz"
        self.obo_file = obo_file or self.base_dir / "go-basic.obo"
        self.obo_subset_file = output_file or self.base_dir / "go-basic-subset.obo"
        self.obo_url = obo_url

        self.skip_prefixes = skip_prefixes or {
            "def", "comment", "xref", "synonym",
            "property_value", "consider", "subset", "alt_id"
        }

    def extract_go_from_emapper_file(self):
        """Extract GO terms and parents from eggnog-mapper annotation file."""

        # Read OBO file to get parent terms
        go_dag = GODag(self.obo_file, load_obsolete=True)

        # Extract GO terms from annotation file
        go_ids = set()
        pattern = re.compile(r"GO:\d{7}")
        with gzip.open(self.emapper_file, "rt") as f:
            for line in f:
                for go_id in pattern.findall(line):
                    go_ids.add(go_id)
                    go_ids.update(go_dag[go_id].get_all_parents())  # Get parent GO terms

        return go_ids

    def download_go_obo(self, obo_path):
        """Download GO basic OBO file."""
        if obo_path.exists():
            return obo_path

        with requests.get(self.obo_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(obo_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)

        return obo_path

    def prepare_filtered_go_obo(self, output_path, cleanup=True):
        """Prepare a subset GO OBO file for testing based on a list of GO terms to keep."""

        obo_path = self.download_go_obo()
        go_ids = self.extract_go_from_emapper_file(obo_path)

        # Ignore unneeded lines with the following prefixes to reduce file size
        skip_line_prefixes = ("def", "comment", "xref", "synonym", "property_value", "consider", "subset", "alt_id")

        gzip_output_path = str(self.obo_subset_file) + ".gz"
        with open(self.obo_file, "r") as r, gzip.open(gzip_output_path, "wt") as out:
            block = []
            go_block = False
            current_id = None

            for line in r:
                line = line.strip()
                if not line:
                    continue

                if line.split(":", 1)[0] in skip_line_prefixes:
                    continue

                if line.startswith("[Term]"):
                    if block and go_block:
                        out.write("\n".join(block) + "\n\n")

                    block = [line]
                    go_block = False
                    current_id = None
                    continue

                block.append(line)
                if line.startswith("id:"):
                    current_id = line.split()[1]
                    if current_id in go_ids:
                        go_block = True

            # last block
            if block and go_block:
                out.write("\n".join(block) + "\n")

        # Remove original OBO file
        if cleanup:
            self.obo_file.unlink(missing_ok=True)

        return gzip_output_path
