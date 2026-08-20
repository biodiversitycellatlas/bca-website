"""Test app utility functions."""

import pytest
from django.test import RequestFactory, TestCase

from app.models import (
    Dataset,
    Domain,
    Gene,
    GeneList,
    Meta,
    MetacellTypeSimilarity,
    Orthogroup,
    Publication,
    Source,
    Species,
)
from app.utils import bioschemas, get_compare_dataset_dict, get_dataset_dict, get_species_dict


class SpeciesDictTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.species = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.dataset = cls.species.datasets.create(name="adult")
        cls.species.meta_set.create(key="species", value="Mus musculus")
        cls.species.meta_set.create(key="phylum", value="Chordata")
        cls.species.meta_set.create(key="kingdom", value="Animalia")

    def test_phylum_searchable_in_dataset_dict(self):
        dataset_dict = get_dataset_dict()
        meta = dataset_dict["Chordata"][0]["meta"]
        assert "Chordata" in meta
        assert "Animalia" in meta
        assert "Mus musculus" not in meta

    def test_phylum_searchable_in_species_dict(self):
        species_dict = get_species_dict()
        meta = species_dict["Chordata"][0]["meta"]
        assert "Chordata" in meta
        assert "Animalia" in meta
        assert "Mus musculus" not in meta


# --- Bioschemas JSON-LD builders (app.utils.bioschemas) ----------------------

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


class TestBioschemasTaxon:
    def test_conforms_to_profile(self, species, request_obj):
        node = bioschemas.Taxon(species, request_obj).build()
        assert_conforms(node, "Taxon")

    def test_maps_species_fields(self, species, request_obj):
        node = bioschemas.Taxon(species, request_obj).build()
        assert node["name"] == "Trichoplax adhaerens"
        assert node["vernacularName"] == "placozoan"
        assert node["description"] == "A small, flat marine animal."
        assert node["image"] == "https://example.org/trichoplax.jpg"
        assert node["additionalType"] == bioschemas.DWC_TAXON

    def test_uses_ncbi_taxon_id_as_identifier(self, species, request_obj):
        node = bioschemas.Taxon(species, request_obj).build()
        assert node["identifier"]["value"] == "10228"
        assert node["identifier"]["url"].endswith("/10228")
        assert node["sameAs"].endswith("/10228")

    def test_identifier_survives_a_taxon_id_without_a_query_term(self, db, request_obj):
        """`createtestdb` records taxon_id without a query_term, so query_url is None."""
        obj = Species.objects.create(scientific_name="Untermed sp.")
        Meta.objects.create(species=obj, key="taxon_id", value="400682")
        identifier = bioschemas.Taxon(obj, request_obj).build()["identifier"]
        assert identifier["value"] == "400682"
        assert "url" not in identifier

    def test_parent_taxon_prefers_most_specific_rank(self, species, request_obj):
        assert bioschemas.Taxon(species, request_obj).build()["parentTaxon"] == "Placozoa"

    def test_nests_conformant_taxon_name(self, species, request_obj):
        assert_conforms(bioschemas.Taxon(species, request_obj).build()["scientificName"], "TaxonName")

    def test_urls_are_absolute(self, species, request_obj):
        node = bioschemas.Taxon(species, request_obj).build()
        assert node["url"].startswith("http://testserver/entry/species/")
        assert node["@id"] == node["url"]

    def test_records_current_page_when_not_canonical(self, species):
        request = RequestFactory().get("/entry/species/")
        node = bioschemas.Taxon(species, request).build()
        assert node["mainEntityOfPage"] == "http://testserver/entry/species/"

    def test_survives_missing_optional_data(self, bare_species, request_obj):
        node = bioschemas.Taxon(bare_species, request_obj).build()
        assert_conforms(node, "Taxon")
        for absent in ("identifier", "sameAs", "vernacularName", "description", "image", "parentTaxon"):
            assert absent not in node

    def test_minimal_form_is_still_conformant(self, species, request_obj):
        node = bioschemas.Taxon(species, request_obj, minimal=True).build()
        assert_conforms(node, "Taxon")
        assert "scientificName" not in node


class TestBioschemasGene:
    def test_conforms_to_profile(self, gene, request_obj):
        assert_conforms(bioschemas.Gene(gene, request_obj).build(), "Gene")

    def test_maps_gene_fields(self, gene, request_obj):
        node = bioschemas.Gene(gene, request_obj).build()
        assert node["name"] == "TAD1"
        assert node["identifier"] == gene.slug
        assert node["description"] == "A gene."

    def test_taxonomic_range_references_species(self, gene, request_obj):
        taxonomic_range = bioschemas.Gene(gene, request_obj).build()["taxonomicRange"]
        assert taxonomic_range["name"] == "Trichoplax adhaerens"
        assert taxonomic_range["@id"].endswith("/entry/species/Trichoplax%20adhaerens/")

    def test_domains_become_biochem_entity_parts(self, gene, request_obj):
        parts = bioschemas.Gene(gene, request_obj).build()["hasBioChemEntityPart"]
        assert [part["name"] for part in parts] == ["PF00069"]
        assert parts[0]["sameAs"].endswith("/pfam/PF00069")

    def test_canonical_url_points_at_entry_page(self, gene):
        request = RequestFactory().get("/atlas/trichoplax-adhaerens-whole-body/gene/TAD1/")
        node = bioschemas.Gene(gene, request).build()
        assert node["url"] == "http://testserver" + gene.get_absolute_url()
        assert node["@id"] == node["url"]
        assert node["mainEntityOfPage"].endswith("/gene/TAD1/")

    def test_omits_main_entity_of_page_on_canonical_url(self, gene):
        request = RequestFactory().get(gene.get_absolute_url())
        assert "mainEntityOfPage" not in bioschemas.Gene(gene, request).build()

    def test_minimal_form_is_still_conformant(self, gene, request_obj):
        node = bioschemas.Gene(gene, request_obj, minimal=True).build()
        assert_conforms(node, "Gene")
        assert "hasBioChemEntityPart" not in node

    def test_tolerates_missing_pfam_source(self, db, species, request_obj):
        obj = Gene.objects.create(species=species, name="NOSRC")
        obj.domains.add(Domain.objects.create(name="PF99999"))
        parts = bioschemas.Gene(obj, request_obj).build()["hasBioChemEntityPart"]
        assert parts[0]["name"] == "PF99999"
        assert "sameAs" not in parts[0]


class TestBioschemasDataset:
    def test_conforms_to_profile(self, dataset, request_obj):
        assert_conforms(bioschemas.Dataset(dataset, request_obj).build(), "Dataset")

    def test_maps_dataset_fields(self, dataset, request_obj):
        node = bioschemas.Dataset(dataset, request_obj).build()
        assert node["name"] == str(dataset)
        assert node["description"] == "Whole-body single-cell atlas."
        assert node["measurementTechnique"] == bioschemas.MEASUREMENT_TECHNIQUE
        assert node["isAccessibleForFree"] is True
        assert node["license"] == bioschemas.get_data_license()

    def test_keywords_include_species_names(self, dataset, request_obj):
        keywords = bioschemas.Dataset(dataset, request_obj).build()["keywords"]
        assert "Trichoplax adhaerens" in keywords
        assert "placozoan" in keywords

    def test_citation_is_a_scholarly_article(self, dataset, request_obj):
        citation = bioschemas.Dataset(dataset, request_obj).build()["citation"]
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
        citation = bioschemas.build_scholarly_article(publication)
        assert {"DOI"} == {each["name"] for each in citation["identifier"]}
        assert all(each["value"] for each in citation["identifier"])

    def test_distributions_cover_the_rest_api(self, dataset, request_obj):
        distributions = bioschemas.Dataset(dataset, request_obj).build()["distribution"]
        formats = {each["encodingFormat"] for each in distributions}
        assert formats == {"application/json", "text/csv", "text/tab-separated-values"}
        dataset_info = [each for each in distributions if "Dataset information" in each["name"]]
        related_data = [each for each in distributions if "Dataset information" not in each["name"]]
        assert len(dataset_info) == 3
        assert all(f"/api/v1/datasets/{dataset.slug}/" in each["contentUrl"] for each in dataset_info)
        assert all(f"dataset={dataset.slug}" in each["contentUrl"] for each in related_data)

    def test_is_included_in_the_portal_catalog(self, dataset, request_obj):
        catalog = bioschemas.Dataset(dataset, request_obj).build()["includedInDataCatalog"]
        assert catalog["@type"] == "DataCatalog"
        assert catalog["url"] == "http://testserver/"

    def test_description_falls_back_to_species(self, db, species):
        obj = Dataset.objects.create(species=species, name="no description")
        assert bioschemas.Dataset(obj).description == species.description

    def test_description_falls_back_to_generated_text(self, db, bare_species):
        obj = Dataset.objects.create(species=bare_species, name="bare")
        description = bioschemas.Dataset(obj).description
        assert "Nemertoderma sp." in description
        assert description

    def test_minimal_form_is_still_conformant(self, dataset, request_obj):
        node = bioschemas.Dataset(dataset, request_obj, minimal=True).build()
        assert_conforms(node, "Dataset")
        assert "distribution" not in node


class TestBioschemasDataCatalog:
    def test_conforms_to_profile(self, db, request_obj):
        assert_conforms(bioschemas.DataCatalog(request_obj).build(), "DataCatalog")

    def test_provider_is_the_bca_organization(self, db, request_obj):
        provider = bioschemas.DataCatalog(request_obj).build()["provider"]
        assert provider["@type"] == "Organization"
        assert provider["name"] == "Biodiversity Cell Atlas"

    def test_url_is_the_current_page(self, db, request_obj):
        node = bioschemas.DataCatalog(request_obj).build()
        assert node["url"] == "http://testserver/entry/species/"
        assert node["@id"] == "http://testserver/"

    def test_lists_conformant_datasets(self, dataset, request_obj):
        node = bioschemas.DataCatalog(request_obj, datasets=[dataset]).build()
        assert len(node["dataset"]) == 1
        assert_conforms(node["dataset"][0], "Dataset")

    def test_omits_empty_dataset_list(self, db, request_obj):
        assert "dataset" not in bioschemas.DataCatalog(request_obj, datasets=[]).build()


class TestBioschemasItemList:
    def test_wraps_stubs_in_a_collection_page(self, species, bare_species, request_obj):
        node = bioschemas.build_item_list_page(
            [species, bare_species],
            request_obj,
            builder=lambda obj, request: bioschemas.Taxon(obj, request, minimal=True).build(),
            name="Species",
        )
        assert node["@type"] == "CollectionPage"
        assert node["name"] == "Species"
        assert node["mainEntity"]["numberOfItems"] == 2
        positions = [each["position"] for each in node["mainEntity"]["itemListElement"]]
        assert positions == [1, 2]
        assert_conforms(node["mainEntity"]["itemListElement"][0]["item"], "Taxon")


class TestBioschemasDropEmpty:
    def test_drops_empty_values_recursively(self):
        compacted = bioschemas._drop_empty({"a": None, "b": "", "c": [], "d": {"e": None}, "f": "keep"})
        assert compacted == {"f": "keep"}

    def test_keeps_booleans_and_zero(self):
        assert bioschemas._drop_empty({"a": False, "b": 0, "c": True}) == {"a": False, "b": 0, "c": True}


class TestBioschemasAbsoluteUrl:
    def test_returns_none_for_a_falsy_url(self, request_obj):
        assert bioschemas._absolute_url(request_obj, "") is None
        assert bioschemas._absolute_url(request_obj, None) is None


class CompareDatasetDictTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Datasets with both SAMap and shared gene module orthogroups
        cls.mouse = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.human = Species.objects.create(scientific_name="Homo sapiens", common_name="human")
        cls.chimp = Species.objects.create(scientific_name="Pan troglodytes", common_name="chimp")

        cls.mouse_dataset = cls.mouse.datasets.create(name="adult")
        cls.human_dataset = cls.human.datasets.create(name="fetal")
        cls.chimp_dataset = cls.chimp.datasets.create(name="adult")
        cls.baby_mouse = cls.mouse.datasets.create(name="baby")

        # SAMap data between mouse and human datasets only
        t1 = cls.mouse_dataset.metacell_types.create(name="cell1")
        t2 = cls.human_dataset.metacell_types.create(name="cell2")
        MetacellTypeSimilarity.objects.create(metacelltype=t1, metacelltype2=t2, samap_score=0.8)

        # Genes and shared orthogroups
        og = Orthogroup.objects.create(name="OG1")
        g_mouse = cls.mouse.genes.create(name="Gene1")
        g_human = cls.human.genes.create(name="Gene2")
        g_chimp = cls.chimp.genes.create(name="Gene3")
        cls.mouse.orthologs.create(orthogroup=og, gene=g_mouse)
        cls.human.orthologs.create(orthogroup=og, gene=g_human)
        cls.chimp.orthologs.create(orthogroup=og, gene=g_chimp)

        # Gene modules containing ortholog-mapped genes
        cls.mouse_dataset.gene_modules.create(name="blue").genes.add(g_mouse)
        cls.human_dataset.gene_modules.create(name="blue").genes.add(g_human)
        cls.chimp_dataset.gene_modules.create(name="blue").genes.add(g_chimp)

    @classmethod
    def datasets(cls, dict_):
        return {elem["dataset"] for elems in dict_.values() for elem in elems}

    def test_includes_datasets_with_samap_and_module_data(self):
        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert self.human_dataset in self.datasets(dict_)

    def test_excludes_current_dataset_and_same_species(self):
        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert self.mouse_dataset not in self.datasets(dict_)
        assert self.baby_mouse not in self.datasets(dict_)

    def test_includes_datasets_with_module_orthogroups_only(self):
        # Chimp shares an orthogroup with mouse but has no SAMap data
        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert self.chimp_dataset in self.datasets(dict_)

    def test_includes_datasets_with_samap_only(self):
        # Dataset with SAMap data but no ortholog-mapped gene modules
        shark = Species.objects.create(scientific_name="Lamna nasus", common_name="shark")
        shark_dataset = shark.datasets.create(name="adult")
        t1 = self.mouse_dataset.metacell_types.create(name="cell3")
        t2 = shark_dataset.metacell_types.create(name="cell4")
        MetacellTypeSimilarity.objects.create(metacelltype=t1, metacelltype2=t2, samap_score=0.5)

        dict_ = get_compare_dataset_dict(self.mouse_dataset)
        assert shark_dataset in self.datasets(dict_)

    def test_excludes_datasets_without_comparison_data(self):
        # Create an isolated species with no SAMap data or shared orthogroups
        snail = Species.objects.create(scientific_name="Cornu aspersum", common_name="snail")
        snail_dataset = snail.datasets.create(name="adult")
        assert snail_dataset not in self.datasets(get_compare_dataset_dict(self.mouse_dataset))
        assert get_compare_dataset_dict(snail_dataset) == {}
        assert get_compare_dataset_dict(None) == {}
