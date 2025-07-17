from django.test import TestCase

from .models import Species, Dataset


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
