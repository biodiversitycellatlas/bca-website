#!/usr/bin/env python3
"""
Download and build a filtered GO basic OBO file for testing the REST API.

Skips fields in GO basic OBO file based on `skip_fields` option.

Python usage:
    # Create file in rest/test/test_fixtures by default
    from scripts.tests.build_go_obo import GeneOntologyOboBuilder
    builder = GeneOntologyOboBuilder()
    builder.prepare_filtered_go_obo()
"""

from pathlib import Path
import gzip
import re
import requests

from goatools.obo_parser import GODag
from scripts.utils.project import get_project_root

class GeneOntologyOboBuilder:
    """Build a filtered GO basic OBO file for testing."""

    def __init__(
        self,
        obo_url = "https://purl.obolibrary.org/obo/go/go-basic.obo",
        base_dir = None,
        emapper_file = None,
        obo_file = None,
        output_file = None,
        skip_fields = None,
    ):
        self.base_dir = base_dir or get_project_root() / "rest" / "tests" / "test_fixtures"

        self.emapper_file = emapper_file or self.base_dir / "emapper_annotation.txt.gz"
        self.obo_file = obo_file or self.base_dir / "go-basic.obo"
        self.output_file = output_file or self.base_dir / "go-basic-subset.obo"

        self.obo_url = obo_url

        self.skip_fields = skip_fields or {
            "def", "comment", "xref", "synonym",
            "property_value", "consider", "subset", "alt_id",
        }

    def extract_go_from_emapper_file(self):
        """Extract GO terms and parent terms from annotation file."""

        # Get parent terms from GO OBO file
        go_dag = GODag(self.obo_file, load_obsolete=True)

        go_ids = set()
        go_pattern = re.compile(r"GO:\d{7}")
        with gzip.open(self.emapper_file, "rt") as f:
            for line in f:
                for go_id in go_pattern.findall(line):
                    if go_id not in go_dag:
                        continue
                    go_ids.add(go_id)
                    go_ids.update(go_dag[go_id].get_all_parents())

        return go_ids

    def download_go_obo(self):
        """Download GO OBO file if missing."""
        if self.obo_file.exists():
            return self.obo_file

        with requests.get(self.obo_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(self.obo_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)

        return self.obo_file

    def prepare_filtered_go_obo(self, cleanup = True):
        """Create gzipped subset OBO containing only relevant GO terms."""
        self.download_go_obo()
        go_ids = self.extract_go_from_emapper_file()
        out_path = self.output_file.with_suffix(self.output_file.suffix + ".gz")

        with open(self.obo_file, "r") as r, gzip.open(out_path, "wt") as out:
            go_block = []
            keep = False

            for raw in r:
                line = raw.rstrip("\n")
                if not line:
                    continue

                # Ignore unneeded lines with the following prefixes to reduce file size
                if line.split(":", 1)[0] in self.skip_fields:
                    continue

                if line.startswith("[Term]"):
                    if keep and go_block:
                        out.write("\n".join(go_block) + "\n\n")

                    go_block = [line]
                    keep = False
                    continue

                go_block.append(line)

                if line.startswith("id:"):
                    go_id = line.split("id:")[1].strip()
                    keep = go_id in go_ids

            # Write last block
            if keep and go_block:
                out.write("\n".join(go_block) + "\n\n")

        if cleanup:
            # Remove original OBO file
            self.obo_file.unlink(missing_ok=True)

        return out_path
