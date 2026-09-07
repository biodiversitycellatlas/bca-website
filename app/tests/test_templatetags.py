import json

import pytest
from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase

from app.models import Publication, Source, Species
from app.templatetags import bioschemas as tags
from app.templatetags.string_extras import (
    split,
    startswith,
    human_number,
    intspace,
)
from app.utils import bioschemas


class StringExtrasTests(SimpleTestCase):
    def test_split_default_delimiter(self):
        assert split("a,b,c") == ["a", "b", "c"]

    def test_split_custom_delimiter(self):
        assert split("a|b|c", "|") == ["a", "b", "c"]

    def test_startswith_true(self):
        assert startswith("django", "dja")

    def test_startswith_false(self):
        assert not startswith("django", "jan")

    def test_human_number_under_1000(self):
        assert human_number(950) == "950"

    def test_human_number_thousands(self):
        assert human_number(1500) == "2K"

    def test_human_number_millions(self):
        assert human_number(2_000_000) == "2M"

    def test_human_number_invalid(self):
        assert human_number("abc") == "abc"

    def test_intspace_integer(self):
        assert intspace(1000000) == "1 000 000"

    def test_intspace_float_integer(self):
        assert intspace(1000.0) == "1 000"

    def test_intspace_float(self):
        assert intspace(1234.56) == "1 234.56"

    def test_intspace_invalid(self):
        assert intspace("abc") == "abc"


# --- Bioschemas JSON-LD tags (app.templatetags.bioschemas) -------------------


@pytest.fixture
def request_obj():
    """Return a request for an arbitrary portal page."""
    return RequestFactory().get("/entry/species/")


@pytest.fixture
def species(db):
    """Return a species."""
    return Species.objects.create(scientific_name="Trichoplax adhaerens", common_name="placozoan")


@pytest.fixture
def dataset(db, species):
    """Return a dataset with a publication."""
    Source.objects.create(name="DOI", url="https://doi.org", query_url="https://doi.org/{{id}}")
    publication = Publication.objects.create(
        title="A cell atlas",
        authors="Darwin, Wallace, Consortium Group",
        year=2025,
        journal="Nature",
        doi="10.1000/abc123",
        pmid="12345678",
    )
    return species.datasets.create(name="whole body", publication=publication)


class TestBioschemasTags:
    @staticmethod
    def render(template, **context):
        """Render a template snippet with the bioschemas tag library loaded."""
        return Template("{% load bioschemas %}" + template).render(Context(context))

    def test_taxon_tag_renders_a_block(self, species, request_obj):
        html = self.render("{% bioschemas_taxon species %}", species=species, request=request_obj)
        assert '<script type="application/ld+json">' in html
        assert '"@type": "Taxon"' in html

    def test_tags_render_nothing_without_an_object(self, request_obj):
        for template in (
            "{% bioschemas_taxon species %}",
            "{% bioschemas_gene gene %}",
            "{% bioschemas_dataset dataset %}",
            "{% bioschemas_species_list species_list %}",
            "{% bioschemas_gene_list genes %}",
        ):
            assert self.render(template, request=request_obj).strip() == ""

    def test_gene_tag_ignores_the_invalid_gene_placeholder(self, request_obj):
        """The Cell Atlas gene view sets `gene` to "" when the gene is unknown."""
        assert self.render("{% bioschemas_gene gene %}", gene="", request=request_obj).strip() == ""

    def test_dataset_tag_ignores_the_invalid_dataset_placeholder(self, request_obj):
        assert self.render("{% bioschemas_dataset dataset %}", dataset="nope", request=request_obj).strip() == ""

    def test_data_catalog_tag_renders_without_arguments(self, db, request_obj):
        html = self.render("{% bioschemas_data_catalog %}", request=request_obj)
        assert '"@type": "DataCatalog"' in html

    def test_download_catalog_tag_lists_species_files(self, db, species, request_obj):
        html = self.render(
            "{% bioschemas_download_catalog species=species_all %}",
            species_all=[species],
            request=request_obj,
        )
        assert '"@type": "DataCatalog"' in html

    def test_tags_work_without_a_request(self, species):
        """Absolute URLs need a request, but a missing one must not break rendering."""
        html = self.render("{% bioschemas_taxon species %}", species=species)
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["url"] == species.get_absolute_url()


class TestBioschemasSerialisation:
    def test_context_is_added_only_at_the_root(self, species, request_obj):
        node = bioschemas.Taxon(species, request_obj).build()
        assert "@context" not in node
        assert "@context" not in node["scientificName"]
        assert bioschemas.build_root(node)["@context"] == bioschemas.CONTEXT

    def test_script_output_is_parseable_json(self, species, request_obj):
        html = tags._script(bioschemas.Taxon(species, request_obj).build())
        assert html.startswith('<script type="application/ld+json">')
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["@type"] == "Taxon"
        assert payload["@context"] == bioschemas.CONTEXT

    def test_script_escapes_html_sensitive_characters(self, db, request_obj):
        obj = Species.objects.create(
            scientific_name="Escapius test",
            description="</script><script>alert(1)</script> & more <b>markup</b>",
        )
        html = tags._script(bioschemas.Taxon(obj, request_obj).build())
        assert "</script><script>" not in html
        assert "\\u003C" in html and "\\u0026" in html
        # The payload still round-trips to the original text
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["description"] == obj.description

    def test_empty_payload_renders_nothing(self):
        assert tags._script(None) == ""
        assert tags._script({}) == ""

    def test_datetimes_are_serialised(self, dataset, request_obj):
        html = tags._script(bioschemas.Dataset(dataset, request_obj).build())
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["dateCreated"].startswith(str(dataset.date_created.year))
