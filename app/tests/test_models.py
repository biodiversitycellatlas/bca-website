import pytest
from django.db import IntegrityError
from django.test import TestCase

from datetime import datetime

from app.models import Publication, Source, Species, DBVersion, GeneModule, Orthogroup


class TestSpeciesModel(TestCase):
    """Test Species model."""

    @classmethod
    def setUpTestData(cls):
        cls.human = Species.objects.create(
            common_name="human",
            scientific_name="Homo sapiens",
            description="random citizen",
        )
        cls.sponge = Species.objects.create(
            common_name="sponge",
            scientific_name="Amphineuron queenslandicum",
            description="random sponge",
        )

    def test_slug(self):
        assert self.human.slug == "homo-sapiens"
        assert self.sponge.slug == "amphineuron-queenslandicum"


class TestDatasetModel(TestCase):
    """Test Dataset model."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.human = Species.objects.create(scientific_name="Homo sapiens")
        cls.sponge = Species.objects.create(scientific_name="Amphineuron queenslandicum")

        cls.baby = cls.human.datasets.create(
            name="baby", image_url="https://upload.wikimedia.org/wikipedia/commons/2/2e/Baby.jpg"
        )
        cls.larva = cls.sponge.datasets.create(name="larva")

    def test_slug(self):
        assert self.baby.slug == "homo-sapiens-baby"
        assert self.larva.slug == "amphineuron-queenslandicum-larva"

    def test_image_source(self):
        assert self.baby.image_source == "Wikimedia"
        assert self.larva.image_source is None


class TestPublicationModel(TestCase):
    """Test Publication model."""

    @classmethod
    def setUpTestData(cls):
        # Create DOI source to test external source links
        Source.objects.create(
            name="DOI", description="DOI Foundation", url="https://doi.org", query_url="https://doi.org/{{id}}"
        )

        cls.dna = Publication.objects.create(
            title="Molecular structure of nucleic acids; a structure for deoxyribose nucleic acid",
            authors="James D Watson, Francis H Crick",
            year=1953,
            journal="Nature",
            pmid=13054692,
            doi="10.1038/171737a0",
        )

        cls.proteins = Publication.objects.create(
            title="The origin and evolution of protein superfamilies",
            authors="Margaret O Dayhoff",
            year=1976,
            journal="Fed Proc",
            pmid=181273,
        )

        cls.genetic_code = Publication.objects.create(
            title="The nucleotide sequence of bacteriophage phiX174",
            authors="Sanger, Coulson, Friedmann, Air, Barrell, Brown, Fiddes, Hutchison, Slocombe, Smith",
            year="1978",
            journal="J Mol Bio",
            pmid=731693,
            doi="10.1016/0022-2836(78)90346-7",
        )

        cls.mouse = Publication.objects.create(
            title="Single-cell transcriptomics of 20 mouse organs creates a Tabula Muris",
            authors="The Tabula Muris Consortium",
            year=2018,
            journal="Nature",
            pmid=30283141,
            doi="10.1038/s41586-018-0590-4",
        )

        cls.standards = Publication.objects.create(
            title="2021 Infusion Therapy Standards of Practice Updates",
            year=2021,
            journal="J Infus Nurs",
            pmid=34197345,
            doi="10.1097/NAN.0000000000000436",
        )

    def test_short_citation(self):
        assert self.dna.create_short_citation() == "Watson & Crick, 1953"
        assert self.proteins.create_short_citation() == "Dayhoff, 1976"
        assert self.genetic_code.create_short_citation() == "Sanger et al., 1978"
        assert self.mouse.create_short_citation() == "The Tabula Muris Consortium, 2018"
        assert self.standards.create_short_citation() == "Unknown, 2021"

    def test_string_representation(self):
        assert str(self.dna) == self.dna.create_short_citation()
        assert str(self.proteins) == self.proteins.create_short_citation()
        assert str(self.mouse) == self.mouse.create_short_citation()

    def test_get_source_html_link(self):
        assert (
            self.dna.get_source_html_link().strip()
            == """
            <a href="https://doi.org/10.1038/171737a0" target="_blank">
                Watson & Crick, 1953
            </a>
            """.strip()
        )

        # If no DOI, return just the short citation information without a link
        assert self.proteins.get_source_html_link() == "Dayhoff, 1976"


class TestGeneModuleMembership(TestCase):
    """Test GeneModuleMembership model."""

    @classmethod
    def setUpTestData(cls):
        human = Species.objects.create(scientific_name="Homo sapiens")
        adult = human.datasets.create(name="adult")

        module = GeneModule.objects.create(dataset=adult, name="black")
        gene = human.genes.create(name="BRCA1")
        cls.membership = gene.modules.create(module=module, membership_score=0.341)

    def test_string_representation(self):
        assert str(self.membership) == "black - BRCA1 - 0.341"


class TestGeneModuleEigengene(TestCase):
    """Test GeneModuleEigengene model."""

    @classmethod
    def setUpTestData(cls):
        human = Species.objects.create(scientific_name="Homo sapiens")
        adult = human.datasets.create(name="adult")

        module = GeneModule.objects.create(dataset=adult, name="black")
        metacell = adult.metacells.create(name="1", x=0.34, y=0.23)
        cls.eigengene_value = module.eigengene_values.create(metacell=metacell, eigengene_value=0.167)

    def test_string_representation(self):
        assert str(self.eigengene_value) == "black - 1 - 0.167"


class TestOrtholog(TestCase):
    """Test Ortholog and Orthogroup models."""

    @classmethod
    def setUpTestData(cls):
        cls.human = Species.objects.create(scientific_name="Homo sapiens")
        mouse = Species.objects.create(scientific_name="Mus musculus")
        rat = Species.objects.create(scientific_name="Rattus norvegicus")
        zebrafish = Species.objects.create(scientific_name="Danio rerio")

        cls.human_brca1 = cls.human.genes.create(name="BRCA1")
        mouse_brca1 = mouse.genes.create(name="Brca1")
        rat_brca1 = rat.genes.create(name="Brca1")
        zebrafish_brca1 = zebrafish.genes.create(name="brca1")

        cls.orthogroup = Orthogroup.objects.create(name="OG1")
        cls.orthogroup.orthologs.create(species=cls.human, gene=cls.human_brca1)
        cls.orthogroup.orthologs.create(species=mouse, gene=mouse_brca1)
        cls.orthogroup.orthologs.create(species=rat, gene=rat_brca1)
        cls.orthogroup.orthologs.create(species=zebrafish, gene=zebrafish_brca1)

    def test_string_representation(self):
        assert str(self.orthogroup) == "OG1 (4 orthologs)"
        for o in self.orthogroup.orthologs.all():
            assert str(o) == f"OG1:{o.gene.name} ({o.species.scientific_name})"

    def test_orthogroup_duplicates(self):
        with pytest.raises(IntegrityError):
            Orthogroup.objects.create(name="OG1")

    def test_ortholog_duplicates(self):
        with pytest.raises(IntegrityError):
            self.orthogroup.orthologs.create(species=self.human, gene=self.human_brca1)


class TestDBVersionModel(TestCase):
    """Test DBVersion model."""

    @classmethod
    def setUpTestData(cls):
        cls.first = DBVersion.objects.create(
            version="v26.2.20", description="First version", commit="cc4a78b24e0edfeb3f80fb5f91b9d4b06cda23ab"
        )
        cls.no_commit = DBVersion.objects.create(version="v26.3.21-demo", description="DB changes")
        cls.no_version = DBVersion.objects.create(
            description="Added new species", commit="43cb01defdb95ca0e76dcfbe13ee4658950abddc"
        )
        cls.shorter_commit = DBVersion.objects.create(description="Changed gene modules", commit="43cb")

    def test_model(self):
        assert self.first.version == "v26.2.20"
        assert self.first.commit == "cc4a78b24e0edfeb3f80fb5f91b9d4b06cda23ab"
        assert self.first.description == "First version"
        assert isinstance(self.first.populated_at, datetime)

        assert self.no_commit.version == "v26.3.21-demo"
        assert self.no_commit.commit is None
        assert self.no_commit.description == "DB changes"
        assert isinstance(self.no_commit.populated_at, datetime)

        assert self.no_version.version is None
        assert self.no_version.commit == "43cb01defdb95ca0e76dcfbe13ee4658950abddc"
        assert self.no_version.description == "Added new species"
        assert isinstance(self.no_version.populated_at, datetime)

        assert self.shorter_commit.version is None
        assert self.shorter_commit.commit == "43cb"
        assert self.shorter_commit.description == "Changed gene modules"
        assert isinstance(self.shorter_commit.populated_at, datetime)

    def test_get_short_commit_length(self):
        assert self.first.get_short_commit() == "cc4a78b"
        assert self.first.get_short_commit(length=10) == "cc4a78b24e"
        assert self.no_commit.get_short_commit() is None
        assert self.shorter_commit.get_short_commit() == "43cb"

    def test_string_representaion(self):
        assert str(self.first) == "v26.2.20 (cc4a78b)"
        assert str(self.no_commit) == "v26.3.21-demo"
        assert str(self.no_version) == "43cb01d"

    def test_invalid_dbversion(self):
        """Using NULL for both version and commit should violate database constraint."""
        with pytest.raises(IntegrityError):
            DBVersion.objects.create(description="Invalid")
