from django.test import TestCase

from app.models import Publication, Source, Species, GeneModule, GeneModuleMembership


class SpeciesModelTest(TestCase):
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
        self.assertEqual(self.human.slug, "homo-sapiens")
        self.assertEqual(self.sponge.slug, "amphineuron-queenslandicum")


class DatasetModelTest(TestCase):
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
        self.assertEqual(self.baby.slug, "homo-sapiens-baby")
        self.assertEqual(self.larva.slug, "amphineuron-queenslandicum-larva")

    def test_image_source(self):
        self.assertEqual(self.baby.image_source, "Wikimedia")
        self.assertEqual(self.larva.image_source, None)


class PublicationModelTest(TestCase):
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
        self.assertEqual(self.dna.create_short_citation(), "Watson & Crick, 1953")
        self.assertEqual(self.proteins.create_short_citation(), "Dayhoff, 1976")
        self.assertEqual(self.genetic_code.create_short_citation(), "Sanger et al., 1978")
        self.assertEqual(self.mouse.create_short_citation(), "The Tabula Muris Consortium, 2018")
        self.assertEqual(self.standards.create_short_citation(), "Unknown, 2021")

    def test_string_representation(self):
        self.assertEqual(str(self.dna), self.dna.create_short_citation())
        self.assertEqual(str(self.proteins), self.proteins.create_short_citation())
        self.assertEqual(str(self.mouse), self.mouse.create_short_citation())

    def test_get_source_html_link(self):
        self.assertEqual(
            self.dna.get_source_html_link().strip(),
            """
            <a href="https://doi.org/10.1038/171737a0" target="_blank">
                Watson & Crick, 1953
            </a>
            """.strip(),
        )

        # If no DOI, return just the short citation information without a link
        self.assertEqual(self.proteins.get_source_html_link(), "Dayhoff, 1976")


class GeneModuleMembershipTest(TestCase):
    """Test GeneModuleMembership model."""

    @classmethod
    def setUpTestData(cls):
        human = Species.objects.create(scientific_name="Homo sapiens")
        adult = human.datasets.create(name="adult")

        module = GeneModule.objects.create(dataset=adult, name="black")
        gene = human.genes.create(name="BRCA1")
        cls.membership = gene.modules.create(module=module, membership_score=0.341)

    def test_string_representation(self):
        self.assertEqual(str(self.membership), "black - BRCA1 - 0.341")


class GeneModuleEigenvalueTest(TestCase):
    """Test GeneModuleEigenvalue model."""

    @classmethod
    def setUpTestData(cls):
        human = Species.objects.create(scientific_name="Homo sapiens")
        adult = human.datasets.create(name="adult")

        module = GeneModule.objects.create(dataset=adult, name="black")
        metacell = adult.metacells.create(name="1", x=0.34, y=0.23)
        cls.eigenvalue = module.eigenvalues.create(metacell=metacell, eigenvalue=0.167)

    def test_string_representation(self):
        self.assertEqual(str(self.eigenvalue), "black - 1 - 0.167")
