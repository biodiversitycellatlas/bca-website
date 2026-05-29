from typing import TextIO

from django.core.management.base import BaseCommand
import factory.random

from app.management.commands import factories
from app.models import Species, Dataset, Publication


def setup_test_environment():
    factory.random.reseed_random("bca_project")


class Command(BaseCommand):
    """
    Creates test database for end-to-end testing.
    """

    def __init__(
        self,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        no_color: bool = False,
        force_color: bool = False,
    ):
        super().__init__(stdout, stderr, no_color, force_color)
        self.sponge = None
        self.homo = None

    def handle(self, *args, **options):
        """
        Database creation
        """
        setup_test_environment()
        self.create_datasets()
        self.create_genes()
        self.stdout.write(self.style.SUCCESS("Successfully created Test Database"))

    def create_datasets(self):
        self.homo = Species.objects.create(
            common_name="human",
            scientific_name="Homo sapiens",
            description="human",
            image_url="https://upload.wikimedia.org/wikipedia/commons/2/2e/Baby.jpg",
        )

        self.sponge = Species.objects.create(
            common_name="sponge",
            scientific_name="Amphineuron queenslandicum",
            description="random sponge",
            image_url="https://upload.wikimedia.org/wikipedia/commons/b/b4/Amphimedon_queenslandica_adult.png",
        )

        HomoPub = Publication.objects.create(
            title="Human Atlas",
            authors="James Gunn",
            year=2024,
            journal="Nature",
            pmid=13054699,
            doi="10.1038/171737a0",
        )

        SpongePub = Publication.objects.create(
            title="Sponge Atlas",
            authors="Mafalda Quin",
            year=2025,
            journal="Fed Proc",
            pmid=181279,
        )

        Dataset.objects.create(
            species=self.homo,
            name="Baby",
            description="human",
            image_url="https://upload.wikimedia.org/wikipedia/commons/2/2e/Baby.jpg",
            publication=HomoPub,
            order=0,
        )

        Dataset.objects.create(
            species=self.sponge,
            name=None,
            description="random sponge",
            image_url="https://upload.wikimedia.org/wikipedia/commons/b/b4/Amphimedon_queenslandica_adult.png",
            publication=SpongePub,
            order=0,
        )

    def create_genes(self):
        factories.GenesFactory.create_batch(10, species=self.sponge)
        factories.GenesFactory.create_batch(12, species=self.homo)
