"""Tests for the Bioschemas JSON-LD builders and template tags."""

import json
import os
import re
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import Context, Template
from django.test import RequestFactory

from app.management.commands import dump_bioschemas
from app.models import Dataset, Domain, Gene, GeneList, Meta, Publication, Source, Species
from app.templatetags import bioschemas as tags
from app.tests.views.utils import DataTestCase
from app.utils import bioschemas

# Required properties per profile, taken from each profile's `$validation.required`
REQUIRED = {
    "Taxon": ["name", "taxonRank"],
    "TaxonName": ["name"],
    "Gene": ["identifier", "name"],
    "Dataset": ["description", "identifier", "keywords", "license", "name", "url"],
    "DataCatalog": ["description", "name", "url", "keywords", "provider"],
}


def assert_conforms(node, profile):
    """Assert a node claims the expected profile and carries its required properties."""
    assert node["@type"] == profile
    assert node["dct:conformsTo"]["@id"] == bioschemas.PROFILES[profile]
    for prop in REQUIRED[profile]:
        assert prop in node, f"{profile} is missing required property '{prop}'"
        assert node[prop] not in (None, "", [], {})


@pytest.fixture
def request_obj():
    """Return a request for an arbitrary portal page."""
    return RequestFactory().get("/entry/species/")


@pytest.fixture
def species(db):
    """Return a species with metadata, an image and a downloadable file."""
    ncbi = Source.objects.create(
        name="NCBI Taxonomy",
        url="https://www.ncbi.nlm.nih.gov/taxonomy",
        query_url="https://www.ncbi.nlm.nih.gov/datasets/taxonomy/{{id}}",
    )
    obj = Species.objects.create(
        scientific_name="Trichoplax adhaerens",
        common_name="placozoan",
        description="A small, flat marine animal.",
        image_url="https://example.org/trichoplax.jpg",
    )
    # `query_term` is what drives Meta.query_url; the ingestion scripts set it
    # alongside `value` (see scripts/data/add_data_to_db.py)
    Meta.objects.create(species=obj, key="taxon_id", value="10228", query_term="10228", source=ncbi)
    Meta.objects.create(species=obj, key="phylum", value="Placozoa")
    Meta.objects.create(species=obj, key="kingdom", value="Metazoa")
    return obj


@pytest.fixture
def bare_species(db):
    """Return a species with no metadata, description or image."""
    return Species.objects.create(scientific_name="Nemertoderma sp.")


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
    return Dataset.objects.create(
        species=species,
        name="whole body",
        description="Whole-body single-cell atlas.",
        publication=publication,
    )


@pytest.fixture
def gene(db, species):
    """Return a gene with a Pfam domain and a gene list."""
    Source.objects.create(
        name="Pfam",
        url="https://www.ebi.ac.uk/interpro/",
        query_url="https://www.ebi.ac.uk/interpro/entry/pfam/{{id}}",
    )
    obj = Gene.objects.create(species=species, name="TAD1", description="A gene.")
    obj.domains.add(Domain.objects.create(name="PF00069"))
    obj.genelists.add(GeneList.objects.create(name="Transcription factors"))
    return obj


# --- Taxon -------------------------------------------------------------------


class TestTaxon:
    def test_conforms_to_profile(self, species, request_obj):
        node = bioschemas.taxon(species, request_obj)
        assert_conforms(node, "Taxon")

    def test_maps_species_fields(self, species, request_obj):
        node = bioschemas.taxon(species, request_obj)
        assert node["name"] == "Trichoplax adhaerens"
        assert node["vernacularName"] == "placozoan"
        assert node["description"] == "A small, flat marine animal."
        assert node["image"] == "https://example.org/trichoplax.jpg"
        assert node["additionalType"] == bioschemas.DWC_TAXON

    def test_uses_ncbi_taxon_id_as_identifier(self, species, request_obj):
        node = bioschemas.taxon(species, request_obj)
        assert node["identifier"]["value"] == "10228"
        assert node["identifier"]["url"].endswith("/10228")
        assert node["sameAs"].endswith("/10228")

    def test_identifier_survives_a_taxon_id_without_a_query_term(self, db, request_obj):
        """`createtestdb` records taxon_id without a query_term, so query_url is None."""
        obj = Species.objects.create(scientific_name="Untermed sp.")
        Meta.objects.create(species=obj, key="taxon_id", value="400682")
        identifier = bioschemas.taxon(obj, request_obj)["identifier"]
        assert identifier["value"] == "400682"
        assert "url" not in identifier

    def test_parent_taxon_prefers_most_specific_rank(self, species, request_obj):
        assert bioschemas.taxon(species, request_obj)["parentTaxon"] == "Placozoa"

    def test_parent_taxon_prefers_division_over_kingdom(self, db, request_obj):
        """`division` is the botanical name for the same rank as `phylum`, so it outranks `kingdom`."""
        obj = Species.objects.create(scientific_name="Arabidopsis thaliana")
        Meta.objects.create(species=obj, key="kingdom", value="Plantae")
        Meta.objects.create(species=obj, key="division", value="Tracheophyta")
        assert bioschemas.taxon(obj, request_obj)["parentTaxon"] == "Tracheophyta"

    def test_nests_conformant_taxon_name(self, species, request_obj):
        assert_conforms(bioschemas.taxon(species, request_obj)["scientificName"], "TaxonName")

    def test_urls_are_absolute(self, species, request_obj):
        node = bioschemas.taxon(species, request_obj)
        assert node["url"].startswith("http://testserver/entry/species/")
        assert node["@id"] == node["url"]

    def test_records_current_page_when_not_canonical(self, species):
        request = RequestFactory().get("/entry/species/")
        node = bioschemas.taxon(species, request)
        assert node["mainEntityOfPage"] == "http://testserver/entry/species/"

    def test_survives_missing_optional_data(self, bare_species, request_obj):
        node = bioschemas.taxon(bare_species, request_obj)
        assert_conforms(node, "Taxon")
        for absent in ("identifier", "sameAs", "vernacularName", "description", "image", "parentTaxon"):
            assert absent not in node

    def test_minimal_form_is_still_conformant(self, species, request_obj):
        node = bioschemas.taxon(species, request_obj, minimal=True)
        assert_conforms(node, "Taxon")
        assert "scientificName" not in node


# --- Gene --------------------------------------------------------------------


class TestGene:
    def test_conforms_to_profile(self, gene, request_obj):
        assert_conforms(bioschemas.gene(gene, request_obj), "Gene")

    def test_maps_gene_fields(self, gene, request_obj):
        node = bioschemas.gene(gene, request_obj)
        assert node["name"] == "TAD1"
        assert node["identifier"] == gene.slug
        assert node["description"] == "A gene."

    def test_taxonomic_range_references_species(self, gene, request_obj):
        taxonomic_range = bioschemas.gene(gene, request_obj)["taxonomicRange"]
        assert taxonomic_range["name"] == "Trichoplax adhaerens"
        assert taxonomic_range["@id"].endswith("/entry/species/Trichoplax%20adhaerens/")

    def test_domains_become_biochem_entity_parts(self, gene, request_obj):
        parts = bioschemas.gene(gene, request_obj)["hasBioChemEntityPart"]
        assert [part["name"] for part in parts] == ["PF00069"]
        assert parts[0]["sameAs"].endswith("/pfam/PF00069")

    def test_canonical_url_points_at_entry_page(self, gene):
        request = RequestFactory().get("/atlas/trichoplax-adhaerens-whole-body/gene/TAD1/")
        node = bioschemas.gene(gene, request)
        assert node["url"] == "http://testserver" + gene.get_absolute_url()
        assert node["@id"] == node["url"]
        assert node["mainEntityOfPage"].endswith("/gene/TAD1/")

    def test_omits_main_entity_of_page_on_canonical_url(self, gene):
        request = RequestFactory().get(gene.get_absolute_url())
        assert "mainEntityOfPage" not in bioschemas.gene(gene, request)

    def test_minimal_form_is_still_conformant(self, gene, request_obj):
        node = bioschemas.gene(gene, request_obj, minimal=True)
        assert_conforms(node, "Gene")
        assert "hasBioChemEntityPart" not in node

    def test_tolerates_missing_pfam_source(self, db, species, request_obj):
        obj = Gene.objects.create(species=species, name="NOSRC")
        obj.domains.add(Domain.objects.create(name="PF99999"))
        parts = bioschemas.gene(obj, request_obj)["hasBioChemEntityPart"]
        assert parts[0]["name"] == "PF99999"
        assert "sameAs" not in parts[0]


# --- Dataset -----------------------------------------------------------------


class TestDataset:
    def test_conforms_to_profile(self, dataset, request_obj):
        assert_conforms(bioschemas.dataset(dataset, request_obj), "Dataset")

    def test_maps_dataset_fields(self, dataset, request_obj):
        node = bioschemas.dataset(dataset, request_obj)
        assert node["name"] == str(dataset)
        assert node["description"] == "Whole-body single-cell atlas."
        assert node["measurementTechnique"] == bioschemas.MEASUREMENT_TECHNIQUE
        assert node["isAccessibleForFree"] is True
        assert node["license"] == bioschemas.data_license()

    def test_keywords_include_species_names(self, dataset, request_obj):
        keywords = bioschemas.dataset(dataset, request_obj)["keywords"]
        assert "Trichoplax adhaerens" in keywords
        assert "placozoan" in keywords

    def test_citation_is_a_scholarly_article(self, dataset, request_obj):
        citation = bioschemas.dataset(dataset, request_obj)["citation"]
        assert citation["@type"] == "ScholarlyArticle"
        assert "dct:conformsTo" not in citation
        assert citation["name"] == "A cell atlas"
        assert citation["datePublished"] == "2025"
        assert {"DOI", "PubMed ID"} == {each["name"] for each in citation["identifier"]}
        assert citation["isPartOf"]["name"] == "Nature"

    def test_scholarly_article_omits_identifiers_without_a_value(self, db):
        publication = Publication.objects.create(
            title="No PubMed entry",
            authors="Solo Author",
            year=2020,
            journal="Journal X",
            doi="10.1000/solo",
            pmid="",
        )
        citation = bioschemas.scholarly_article(publication)
        assert {"DOI"} == {each["name"] for each in citation["identifier"]}
        assert all(each["value"] for each in citation["identifier"])

    def test_distributions_cover_the_rest_api(self, dataset, request_obj):
        distributions = bioschemas.dataset(dataset, request_obj)["distribution"]
        formats = {each["encodingFormat"] for each in distributions}
        assert formats == {"application/json", "text/csv", "text/tab-separated-values"}
        assert all(f"dataset={dataset.slug}" in each["contentUrl"] for each in distributions)

    def test_is_included_in_the_portal_catalog(self, dataset, request_obj):
        catalog = bioschemas.dataset(dataset, request_obj)["includedInDataCatalog"]
        assert catalog["@type"] == "DataCatalog"
        assert catalog["url"] == "http://testserver/"

    def test_description_falls_back_to_species(self, db, species):
        obj = Dataset.objects.create(species=species, name="no description")
        assert bioschemas.dataset_description(obj) == species.description

    def test_description_falls_back_to_generated_text(self, db, bare_species):
        obj = Dataset.objects.create(species=bare_species, name="bare")
        description = bioschemas.dataset_description(obj)
        assert "Nemertoderma sp." in description
        assert description

    def test_minimal_form_is_still_conformant(self, dataset, request_obj):
        node = bioschemas.dataset(dataset, request_obj, minimal=True)
        assert_conforms(node, "Dataset")
        assert "distribution" not in node


# --- DataCatalog -------------------------------------------------------------


class TestDataCatalog:
    def test_conforms_to_profile(self, db, request_obj):
        assert_conforms(bioschemas.data_catalog(request_obj), "DataCatalog")

    def test_provider_is_the_bca_organization(self, db, request_obj):
        provider = bioschemas.data_catalog(request_obj)["provider"]
        assert provider["@type"] == "Organization"
        assert provider["name"] == "Biodiversity Cell Atlas"

    def test_url_is_the_current_page(self, db, request_obj):
        node = bioschemas.data_catalog(request_obj)
        assert node["url"] == "http://testserver/entry/species/"
        assert node["@id"] == "http://testserver/"

    def test_lists_conformant_datasets(self, dataset, request_obj):
        node = bioschemas.data_catalog(request_obj, datasets=[dataset])
        assert len(node["dataset"]) == 1
        assert_conforms(node["dataset"][0], "Dataset")

    def test_omits_empty_dataset_list(self, db, request_obj):
        assert "dataset" not in bioschemas.data_catalog(request_obj, datasets=[])


# --- list pages --------------------------------------------------------------


class TestItemList:
    def test_wraps_stubs_in_a_collection_page(self, species, bare_species, request_obj):
        node = bioschemas.item_list(
            [species, bare_species],
            request_obj,
            builder=lambda obj, request: bioschemas.taxon(obj, request, minimal=True),
            name="Species",
        )
        assert node["@type"] == "CollectionPage"
        assert node["name"] == "Species"
        assert node["mainEntity"]["numberOfItems"] == 2
        positions = [each["position"] for each in node["mainEntity"]["itemListElement"]]
        assert positions == [1, 2]
        assert_conforms(node["mainEntity"]["itemListElement"][0]["item"], "Taxon")


# --- serialisation and escaping ----------------------------------------------


class TestSerialisation:
    def test_context_is_added_only_at_the_root(self, species, request_obj):
        node = bioschemas.taxon(species, request_obj)
        assert "@context" not in node
        assert "@context" not in node["scientificName"]
        assert bioschemas.as_root(node)["@context"] == bioschemas.CONTEXT

    def test_script_output_is_parseable_json(self, species, request_obj):
        html = tags._script(bioschemas.taxon(species, request_obj))
        assert html.startswith('<script type="application/ld+json">')
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["@type"] == "Taxon"
        assert payload["@context"] == bioschemas.CONTEXT

    def test_script_escapes_html_sensitive_characters(self, db, request_obj):
        obj = Species.objects.create(
            scientific_name="Escapius test",
            description="</script><script>alert(1)</script> & more <b>markup</b>",
        )
        html = tags._script(bioschemas.taxon(obj, request_obj))
        assert "</script><script>" not in html
        assert "\\u003C" in html and "\\u0026" in html
        # The payload still round-trips to the original text
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["description"] == obj.description

    def test_empty_payload_renders_nothing(self):
        assert tags._script(None) == ""
        assert tags._script({}) == ""

    def test_datetimes_are_serialised(self, dataset, request_obj):
        html = tags._script(bioschemas.dataset(dataset, request_obj))
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["dateCreated"].startswith(str(dataset.date_created.year))


class TestCompact:
    def test_drops_empty_values_recursively(self):
        compacted = bioschemas._compact({"a": None, "b": "", "c": [], "d": {"e": None}, "f": "keep"})
        assert compacted == {"f": "keep"}

    def test_keeps_booleans_and_zero(self):
        assert bioschemas._compact({"a": False, "b": 0, "c": True}) == {"a": False, "b": 0, "c": True}


class TestAbsolute:
    def test_returns_none_for_a_falsy_url(self, request_obj):
        assert bioschemas._absolute(request_obj, "") is None
        assert bioschemas._absolute(request_obj, None) is None


# --- template tags -----------------------------------------------------------


def render(template, **context):
    """Render a template snippet with the bioschemas tag library loaded."""
    return Template("{% load bioschemas %}" + template).render(Context(context))


class TestTemplateTags:
    def test_taxon_tag_renders_a_block(self, species, request_obj):
        html = render("{% bioschemas_taxon species %}", species=species, request=request_obj)
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
            assert render(template, request=request_obj).strip() == ""

    def test_gene_tag_ignores_the_invalid_gene_placeholder(self, request_obj):
        """The Cell Atlas gene view sets `gene` to "" when the gene is unknown."""
        assert render("{% bioschemas_gene gene %}", gene="", request=request_obj).strip() == ""

    def test_dataset_tag_ignores_the_invalid_dataset_placeholder(self, request_obj):
        assert render("{% bioschemas_dataset dataset %}", dataset="nope", request=request_obj).strip() == ""

    def test_data_catalog_tag_renders_without_arguments(self, db, request_obj):
        html = render("{% bioschemas_data_catalog %}", request=request_obj)
        assert '"@type": "DataCatalog"' in html

    def test_download_catalog_tag_lists_species_files(self, db, species, request_obj):
        html = render(
            "{% bioschemas_download_catalog species=species_all %}",
            species_all=[species],
            request=request_obj,
        )
        assert '"@type": "DataCatalog"' in html

    def test_tags_work_without_a_request(self, species):
        """Absolute URLs need a request, but a missing one must not break rendering."""
        html = render("{% bioschemas_taxon species %}", species=species)
        payload = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert payload["url"] == species.get_absolute_url()


# --- rendered pages ----------------------------------------------------------


JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


class BioschemasPageTests(DataTestCase):
    """Check that each candidate page serves parseable, conformant JSON-LD."""

    def payloads(self, url):
        """Return the parsed JSON-LD blocks served by `url`."""
        response = self.client.get(url)
        assert response.status_code == 200, f"{url} returned {response.status_code}"
        blocks = JSONLD.findall(response.content.decode())
        assert blocks, f"{url} served no JSON-LD"
        return [json.loads(block) for block in blocks]

    def assert_page(self, url, type_, profile=None):
        """Assert `url` serves exactly one JSON-LD block of the expected type."""
        payloads = self.payloads(url)
        assert len(payloads) == 1, f"{url} served {len(payloads)} JSON-LD blocks"

        payload = payloads[0]
        assert payload["@context"] == bioschemas.CONTEXT
        assert payload["@type"] == type_
        if profile:
            assert_conforms(payload, profile)
        return payload

    def test_home_serves_a_data_catalog(self):
        self.assert_page("/", "DataCatalog", "DataCatalog")

    def test_downloads_serves_a_data_catalog(self):
        payload = self.assert_page("/downloads/", "DataCatalog", "DataCatalog")
        names = [each["name"] for each in payload["distribution"]]
        assert self.mouse_fasta.label in names

    def test_species_detail_serves_a_taxon(self):
        payload = self.assert_page(f"/entry/species/{self.mouse}/", "Taxon", "Taxon")
        assert payload["name"] == "Mus musculus"
        assert payload["vernacularName"] == "mouse"

    def test_species_list_serves_a_collection_page(self):
        payload = self.assert_page("/entry/species/", "CollectionPage")
        names = [each["item"]["name"] for each in payload["mainEntity"]["itemListElement"]]
        assert "Mus musculus" in names

    def test_dataset_list_serves_a_data_catalog(self):
        payload = self.assert_page("/entry/dataset/", "DataCatalog", "DataCatalog")
        assert len(payload["dataset"]) == Dataset.objects.count()
        for each in payload["dataset"]:
            assert_conforms(each, "Dataset")

    def test_gene_detail_serves_a_gene(self):
        payload = self.assert_page(f"/entry/gene/{self.mouse.slug}/{self.brca1.name}/", "Gene", "Gene")
        assert payload["name"] == "Brca1"
        assert payload["taxonomicRange"]["name"] == "Mus musculus"
        assert {each["name"] for each in payload["hasBioChemEntityPart"]} == {
            domain.name for domain in self.brca1_domains
        }

    def test_gene_list_serves_a_collection_page(self):
        payload = self.assert_page(f"/entry/gene/{self.mouse.slug}/", "CollectionPage")
        assert payload["mainEntity"]["numberOfItems"] == self.mouse.genes.count()

    def test_atlas_dataset_serves_a_dataset(self):
        payload = self.assert_page(f"/atlas/{self.adult_mouse.slug}/", "Dataset", "Dataset")
        assert payload["name"] == str(self.adult_mouse)
        assert payload["about"]["name"] == "Mus musculus"

    def test_atlas_gene_page_points_at_the_canonical_gene(self):
        url = f"/atlas/{self.adult_mouse.slug}/gene/{self.brca1.name}/"
        payload = self.assert_page(url, "Gene", "Gene")
        assert payload["url"].endswith(self.brca1.get_absolute_url())
        assert payload["mainEntityOfPage"].endswith(url)

    def test_atlas_gene_page_is_silent_for_an_unknown_gene(self):
        response = self.client.get(f"/atlas/{self.adult_mouse.slug}/gene/nope/")
        assert response.status_code == 200
        assert not JSONLD.findall(response.content.decode())

    def test_dump_command_reports_every_page(self):
        """`dump_bioschemas` is the paste-into-a-validator helper (see the report, §8.3)."""
        out = StringIO()
        call_command("dump_bioschemas", stdout=out)
        output = out.getvalue()

        assert "NO JSON-LD" not in output
        assert "pages served JSON-LD." in output
        for profile in ("Taxon/1.0-RELEASE", "Gene/1.0-RELEASE", "Dataset/1.0-RELEASE"):
            assert profile in output, f"no page reported {profile}"

    def test_dump_command_raw_mode_emits_only_json(self):
        out = StringIO()
        call_command("dump_bioschemas", f"/atlas/{self.adult_mouse.slug}/", "--raw", stdout=out)
        payload = json.loads(out.getvalue())
        assert_conforms(payload, "Dataset")

    def dumped_url(self, env, *args):
        """Return the `url` of the payload dumped for a gene page under `env`."""
        url = f"/entry/gene/{self.mouse.slug}/{self.brca1.name}/"
        out = StringIO()
        with mock.patch.dict(os.environ, env, clear=True):
            call_command("dump_bioschemas", url, "--raw", *args, stdout=out)
        return json.loads(out.getvalue())["url"], url

    def test_dump_command_builds_urls_from_django_hostname(self):
        """`DJANGO_HOSTNAME` is set in every environment, so it is the natural default."""
        built, url = self.dumped_url({"DJANGO_HOSTNAME": "portal.example.org"})
        assert built == f"http://portal.example.org{url}"

    def test_dump_command_adds_web_port_outside_production(self):
        """`DJANGO_HOSTNAME` is a bare hostname, but dev nginx publishes on WEB_PORT."""
        built, url = self.dumped_url({"DJANGO_HOSTNAME": "portal-bca-gambusia", "WEB_PORT": "8081"})
        assert built == f"http://portal-bca-gambusia:8081{url}"

    def test_dump_command_omits_web_port_in_production(self):
        """Production nginx serves DJANGO_HOSTNAME on 443, so no port belongs in the URL."""
        env = {"DJANGO_HOSTNAME": "portal.example.org", "WEB_PORT": "8081", "ENVIRONMENT": "prod"}
        built, url = self.dumped_url(env)
        assert built == f"https://portal.example.org{url}"

    def test_dump_command_host_option_overrides_the_environment(self):
        env = {"DJANGO_HOSTNAME": "portal.example.org", "WEB_PORT": "8081"}
        built, url = self.dumped_url(env, "--host", "portal-bca-gambusia:8000")
        assert built == f"http://portal-bca-gambusia:8000{url}"

    def test_dump_command_scheme_option_overrides_the_environment(self):
        built, url = self.dumped_url({"DJANGO_HOSTNAME": "portal.example.org"}, "--scheme", "https")
        assert built == f"https://portal.example.org{url}"

    def test_dump_command_falls_back_without_django_hostname(self):
        built, url = self.dumped_url({})
        assert built == f"http://{dump_bioschemas.FALLBACK_HOST}{url}"

    def test_dump_command_fails_when_a_page_serves_nothing(self):
        """Non-zero exit makes it usable as a CI check that markup has not vanished."""
        with pytest.raises(CommandError, match="No JSON-LD served by"):
            call_command("dump_bioschemas", "/about/", stdout=StringIO())

    def test_pages_without_a_matching_profile_serve_no_jsonld(self):
        """Tier 3 pages are deliberately left without structured data."""
        for url in (
            "/entry/",
            "/entry/domain/",
            f"/entry/domain/{self.brca1_domains[0].name}/",
            "/entry/orthogroup/",
            f"/entry/orthogroup/{self.og1.name}/",
            f"/entry/gene-module/{self.adult_mouse.slug}/{self.gene_module.name}/",
            "/about/",
            "/search/",
        ):
            response = self.client.get(url)
            assert response.status_code == 200, f"{url} returned {response.status_code}"
            assert not JSONLD.findall(response.content.decode()), f"{url} unexpectedly served JSON-LD"
