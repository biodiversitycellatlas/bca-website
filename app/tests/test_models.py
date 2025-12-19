from django.test import TestCase

from ..models import Dataset, Publication, Source, Species


class SpeciesModelTest(TestCase):
    def setUp(self):
        self.human = Species.objects.create(
            common_name="human",
            scientific_name="Homo sapiens",
            description="random citizen",
        )
        self.sponge = Species.objects.create(
            common_name="sponge",
            scientific_name="Amphineuron queenslandicum",
            description="random sponge citizen",
        )

    def test_slug(self):
        self.assertEqual(self.human.slug, "homo-sapiens")
        self.assertEqual(self.sponge.slug, "amphineuron-queenslandicum")


class DatasetModelTest(SpeciesModelTest):
    def setUp(self):
        super().setUp()
        self.baby = Dataset(species=self.human, name="Baby")
        self.larva = Dataset(species=self.sponge, name="Larva")

    def test_slug(self):
        self.assertEqual(self.baby.slug, "homo-sapiens-baby")
        self.assertEqual(self.larva.slug, "amphineuron-queenslandicum-larva")


class PublicationModelTest(TestCase):
    def setUp(self):
        # Create DOI source to test external source links
        Source.objects.create(
            name="DOI",
            description="DOI Foundation",
            url="https://doi.org",
            query_url="https://doi.org/{{id}}"
        )

        self.dna = Publication.objects.create(
            title="Molecular structure of nucleic acids; a structure for deoxyribose nucleic acid",
            authors="James D Watson, Francis H Crick",
            year=1953,
            journal="Nature",
            pubmed_id=13054692,
            doi="10.1038/171737a0"
        )

        self.proteins = Publication.objects.create(
            title="The origin and evolution of protein superfamilies",
            authors="Margaret O Dayhoff",
            year=1976,
            journal="Fed Proc",
            pubmed_id=181273
        )

        self.genetic_code = Publication.objects.create(
            title="The nucleotide sequence of bacteriophage phiX174",
            authors="F Sanger, A R Coulson, T Friedmann, G M Air, B G Barrell, N L Brown, J C Fiddes, C A Hutchison 3rd, P M Slocombe, M Smith",
            year="1978",
            journal="J Mol Bio",
            pubmed_id=731693,
            doi="10.1016/0022-2836(78)90346-7",
        )

        self.standards = Publication.objects.create(
            title="2021 Infusion Therapy Standards of Practice Updates",
            year=2021,
            journal="J Infus Nurs",
            pubmed_id=34197345,
            doi="10.1097/NAN.0000000000000436"
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
            """.strip()
        )

        # If no DOI, return just the short citation information without a link
        self.assertEqual(self.proteins.get_source_html_link(), "Dayhoff, 1976")
