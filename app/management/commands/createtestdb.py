import itertools
from random import random
from typing import TextIO

import factory.random
from django.core.management.base import BaseCommand

from app.management.commands import factories
from app.models import Species, Dataset, Domain, Publication, GeneList, Gene, Metacell, MetacellLink


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
        self.create_gene_modules()
        self.create_orthogroups()
        self.create_metacells()
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
        factories.DomainFactory.create_batch(6)
        factories.GeneListFactory.create_batch(8)
        domains = list(Domain.objects.all())
        genelists = list(GeneList.objects.all())
        factories.GenesFactory.create_batch(
            size=10,
            species=self.sponge,
            domains=(domains[0], domains[2]),
            genelists=(genelists[1], genelists[4]),
        )
        factories.GenesFactory.create_batch(
            size=12,
            species=self.homo,
            domains=(domains[1], domains[3]),
            genelists=(genelists[0], genelists[3]),
        )

    def create_gene_modules(self):
        sponge_dataset = Dataset.objects.get(species=self.sponge)
        homo_dataset = Dataset.objects.get(species=self.homo)
        sponge_genes = list(Gene.objects.filter(species=self.sponge))
        homo_genes = list(Gene.objects.filter(species=self.homo))
        factories.GeneModuleFactory.create_batch(
            size=3,
            dataset=sponge_dataset,
            genes=(sponge_genes[0], sponge_genes[1]),
        )
        factories.GeneModuleFactory.create_batch(
            size=4,
            dataset=homo_dataset,
            genes=(homo_genes[1], homo_genes[2], homo_genes[3]),
        )

    def create_orthogroups(self):
        sponge_genes = list(Gene.objects.filter(species=self.sponge))
        homo_genes = list(Gene.objects.filter(species=self.homo))

        orthogroup0 = factories.OrthoGroupFactory.create()
        orthogroup1 = factories.OrthoGroupFactory.create()

        factories.OrthologFactory.create(species=self.sponge, gene=sponge_genes[0], orthogroup=orthogroup0)
        factories.OrthologFactory.create(species=self.sponge, gene=sponge_genes[1], orthogroup=orthogroup0)
        factories.OrthologFactory.create(species=self.homo, gene=homo_genes[1], orthogroup=orthogroup0)

        factories.OrthologFactory.create(species=self.sponge, gene=sponge_genes[2], orthogroup=orthogroup1)
        factories.OrthologFactory.create(species=self.sponge, gene=sponge_genes[3], orthogroup=orthogroup1)
        factories.OrthologFactory.create(species=self.homo, gene=homo_genes[2], orthogroup=orthogroup1)

    def create_metacell_links(self, dataset, metacells):
        for m1, m2 in itertools.combinations(metacells, 2):
            if random() < 0.2:
                MetacellLink.objects.create(dataset=dataset, metacell=m1, metacell2=m2)

    def create_metacells(self):
        sponge_dataset = Dataset.objects.get(species=self.sponge)
        homo_dataset = Dataset.objects.get(species=self.homo)

        factories.MetaCellTypeFactory.create_batch(size=9, dataset=sponge_dataset)
        factories.MetaCellTypeFactory.create_batch(size=9, dataset=homo_dataset)

        factories.MetacellCountFactory.create_batch(size=12, dataset=homo_dataset)
        factories.MetacellCountFactory.create_batch(size=18, dataset=sponge_dataset)

        sponge_metacells = Metacell.objects.filter(dataset=sponge_dataset)
        homo_metacells = Metacell.objects.filter(dataset=homo_dataset)
        self.create_metacell_links(sponge_dataset, sponge_metacells)
        self.create_metacell_links(homo_dataset, homo_metacells)
