from django.test import TestCase

from app.models import Dataset, Publication, Source, Species


class SpeciesModelTest(TestCase):
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


class DatasetModelTest(SpeciesModelTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.baby = Dataset(
            species=cls.human,
            name="Baby",
            image_url="https://upload.wikimedia.org/wikipedia/commons/2/2e/Baby.jpg"
        )
        cls.larva = Dataset(species=cls.sponge, name="Larva")

    def test_slug(self):
        self.assertEqual(self.baby.slug, "homo-sapiens-baby")
        self.assertEqual(self.larva.slug, "amphineuron-queenslandicum-larva")

    def test_image_source(self):
        self.assertEqual(self.baby.image_source, "Wikimedia")
        self.assertEqual(self.larva.image_source, None)


class PublicationModelTest(TestCase):
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
        self.assertEqual(self.standards.create_short_citation(), "Unknown, 2021")

    def test_string_representation(self):
        self.assertEqual(str(self.dna), "Watson & Crick, 1953")
        self.assertEqual(str(self.proteins), "Dayhoff, 1976")

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
