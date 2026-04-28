import tempfile
import gzip
import requests
import re
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from goatools.obo_parser import GODag

from app.models import (
    Species,
    GlobalFile,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class EnrichmentAnalysisTests(APITestCase):
    """Tests enrichment endpoint."""

    def extract_go_from_emapper_file(
        self, obo_path, file_path=Path(__file__).parent / "test_fixtures" / "emapper_annotation.txt.gz"
    ):
        """Extract all GO terms from annotation file."""

        # Expand GO terms from OBO file to include all parent terms
        go_dag = GODag(obo_path, load_obsolete=True)

        go_ids = set()
        pattern = re.compile(r"GO:\d{7}")

        with gzip.open(file_path, "rt") as f:
            for line in f:
                for go_id in pattern.findall(line):
                    go_ids.add(go_id)
                    go_ids.update(go_dag[go_id].get_all_parents())

        return go_ids

    def download_go_obo(self, output_path=Path(__file__).parent / "test_fixtures" / "go-basic.obo"):
        """Download GO basic OBO file."""
        if output_path.exists():
            return output_path

        url = "https://purl.obolibrary.org/obo/go/go-basic.obo"
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)

        return output_path

    def prepare_filtered_go_obo(self, output_path=Path(__file__).parent / "test_fixtures" / "go-basic-subset.obo"):
        """Prepare a subset GO OBO file for testing based on a list of GO terms to keep."""

        obo_path = self.download_go_obo()
        go_ids = self.extract_go_from_emapper_file(obo_path)

        # Ignore unneeded lines with the following prefixes to reduce file size
        skip_line_prefixes = ("def", "comment", "xref", "synonym", "property_value", "consider", "subset", "alt_id")

        gzip_output_path = str(output_path) + ".gz"
        with open(obo_path, "r") as r, gzip.open(gzip_output_path, "wt") as out:
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
        obo_path.unlink()

        return gzip_output_path

    @classmethod
    def setUpTestData(cls):
        aque = Species.objects.create(scientific_name="Amphimedon queenslandica")
        aque_adult = aque.datasets.create(name="adult")

        # Get OBO file with GO term definitions
        go_obo_compressed = Path(__file__).parent / "test_fixtures" / "go-basic-subset.obo.gz"
        with gzip.open(go_obo_compressed, "rb") as f:
            go_obo_file = f.read()
        cls.go_obo = GlobalFile.objects.create(
            type="go-basic-obo", file=SimpleUploadedFile("go-basic.obo", go_obo_file)
        )

        # Get functional annotation
        emapper_file = Path(__file__).parent / "test_fixtures" / "emapper_annotation.txt.gz"
        cls.emapper = aque.files.create(
            type="eggnog-mapper", file=SimpleUploadedFile("emapper.txt.gz", emapper_file.read_bytes())
        )

        # Prepare background genes: add genes to metacell gene expression based on functional annotation
        mc1 = aque_adult.metacells.create(name="mc1", x="1", y="5")
        cls.genes = []
        with gzip.open(emapper_file, "rt") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                gene = line.split("\t")[0]
                g = aque.genes.create(name=gene)
                aque_adult.mge.create(gene=g, metacell=mc1)
                cls.genes.append(gene)

    def check_enrichment_response(self, response, genes, obsolete=False):
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for d in response.data:
            self.assertRegex(d["term"], r"^GO:\d{7}$", "Expected GO term name")
            self.assertIn(d["enrichment"], {"e", "p"}, "Enrichment results")

            if obsolete:
                self.assertGreaterEqual(d["depth"], 0, "GO term depth ≥ 0")

                # Check if returning any obsolete GO term
                self.assertTrue(
                    any(d.get("is_obsolete") for d in response.data), "Expected at least one obsolete term in response"
                )

                # Check if the obsolete status matches the OBO definition
                go_obo = GODag(self.go_obo.file.path, load_obsolete=True, prt=None)
                for d in response.data:
                    self.assertEqual(go_obo[d["term"]].is_obsolete, d.get("is_obsolete"))
            else:
                self.assertGreaterEqual(d["depth"], 1, "GO term depth ≥ 1")
                self.assertNotIn("is_obsolete", d, "No obsolete field")

            self.assertSetEqual(set(d["genes"]), genes, "Genes match input in these examples")
            self.assertEqual(d["query_count"], len(d["genes"]), "Match number of genes")
            self.assertEqual(d["query_hit_count"], len(d["genes"]), "Match number of genes")
            self.assertEqual(d["background_hit_count"], len(d["genes"]), "Match number of genes")
            self.assertEqual(d["background_count"], len(self.genes), "Match all genes")

            self.assertTrue(0 <= d["pvalue"] <= 1, "Expected p-value")
            self.assertTrue(0 <= d["qvalue"] <= 1, "Expected adjusted p-value")
            self.assertLess(d["pvalue"], 0.05, "Significant p-value")
            self.assertLess(d["qvalue"], 0.05, "Significant q-value")
            self.assertLessEqual(d["pvalue"], d["qvalue"], "p-value ≤ adjusted p-value")

            self.assertIn(d["namespace"], {"BP", "CC", "MF"}, "Match specific namespaces")
            self.assertTrue(
                all(isinstance(x, float) for x in d["similarity_coords"]),
                "similarity_coords is a tuple of two numbers",
            )

    def test_post(self):
        url = "/api/v1/enrichment/"
        genes = {"Aque_Aqu2.1.30266_001", "Aque_Aqu2.1.30264_001", "Aque_Aqu2.1.30269_001"}
        data = dict(dataset="amphimedon-queenslandica-adult", genes=genes)
        response = self.client.post(url, data, format="json")
        self.check_enrichment_response(response, genes)

        for d in response.data:
            self.assertIn(
                d["term"],
                {
                    "GO:0006436",
                    "GO:0006518",
                    "GO:0006412",
                    "GO:0048813",
                    "GO:0004830",
                    "GO:0010835",
                    "GO:0016874",
                    "GO:0031334",
                    "GO:0016875",
                    "GO:0043043",
                    "GO:0043038",
                    "GO:0140101",
                    "GO:0043039",
                },
                "Expected GO terms",
            )

        # Test with valid and invalid genes: silently ignores invalid genes
        invalid_genes = {"random", "arbitrary", "gene"}
        valid_genes = {"Aque_Aqu2.1.30266_001", "Aque_Aqu2.1.30264_001", "Aque_Aqu2.1.30269_001"}
        genes = invalid_genes | valid_genes

        data = dict(dataset="amphimedon-queenslandica-adult", genes=genes)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.check_enrichment_response(response, valid_genes)

    def test_post_obsolete(self):
        """Test if obsolete terms are included."""
        url = "/api/v1/enrichment/"
        genes = {"Aque_Aqu2.1.30266_001", "Aque_Aqu2.1.30264_001", "Aque_Aqu2.1.30269_001"}
        data = dict(dataset="amphimedon-queenslandica-adult", genes=genes, obsolete=True)
        response = self.client.post(url, data, format="json")
        self.check_enrichment_response(response, genes, obsolete=True)

        for d in response.data:
            self.assertIn(
                d["term"],
                {
                    "GO:0048813",
                    "GO:0004830",
                    "GO:0031334",
                    "GO:0006412",
                    "GO:0010835",
                    "GO:0043604",
                    "GO:0043603",
                    "GO:0006436",
                    "GO:0016875",
                    "GO:0043038",
                    "GO:0016874",
                    "GO:0043043",
                    "GO:0043039",
                    "GO:0006518",
                    "GO:0140101",
                },
                "Expected GO terms",
            )

    def test_post_no_enrichment(self):
        """Test no enrichment results."""

        url = "/api/v1/enrichment/"
        genes = {"Aque_Aqu2.1.30266_001", "Aque_Aqu2.1.30264_001"}
        data = dict(dataset="amphimedon-queenslandica-adult", genes=genes)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_post_invalid(self):
        """Test invalid input."""
        url = "/api/v1/enrichment/"

        # No dataset in request
        data = dict(genes=[])
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field is required.", response.data["dataset"])

        # Wrong dataset name
        genes = {"Aque_Aqu2.1.30266_001", "Aque_Aqu2.1.30264_001", "Aque_Aqu2.1.30269_001"}
        data = dict(dataset="random-dataset", genes=genes)

        with self.assertRaises(ValueError) as ctx:
            response = self.client.post(url, data, format="json")

        self.assertIn(
            "Cannot find dataset for random-dataset",
            str(ctx.exception)
        )

        # No genes in request
        data = dict(dataset="amphimedon-queenslandica-adult")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn(
            "At least one of 'genes', 'gene_modules', or 'gene_lists' must be provided.",
            response.data["non_field_errors"],
        )

        # Empty gene array
        data = dict(dataset="amphimedon-queenslandica-adult", genes=[])
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

        # Non-existing genes
        genes = ["random", "arbitrary", "gene"]
        data = dict(dataset="amphimedon-queenslandica-adult", genes=genes)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.data["detail"])
