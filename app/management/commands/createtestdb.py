import itertools
import os
import random
from typing import TextIO

import factory.random
import h5py
import numpy as np
from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand
from faker import Faker

from app.management.commands import factories
from app.models import (
    Species,
    Dataset,
    Domain,
    Publication,
    GeneList,
    Gene,
    Metacell,
    MetacellLink,
    SingleCell,
    Source,
    DatasetFile,
)


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
        self.sponge_dataset = None
        self.homo_dataset = None

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
        self.create_singlecells()
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

        Source.objects.create(
            name="DOI", description="DOI Foundation", url="https://doi.org", query_url="https://doi.org/{{id}}"
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
            doi="10.1038/89764301",
        )

        self.homo_dataset = Dataset.objects.create(
            species=self.homo,
            name="Baby",
            description="human",
            image_url="https://upload.wikimedia.org/wikipedia/commons/2/2e/Baby.jpg",
            publication=HomoPub,
            order=0,
        )

        self.sponge_dataset = Dataset.objects.create(
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
        sponge_genes = list(Gene.objects.filter(species=self.sponge))
        homo_genes = list(Gene.objects.filter(species=self.homo))
        factories.GeneModuleFactory.create_batch(
            size=3,
            dataset=self.sponge_dataset,
            genes=(sponge_genes[0], sponge_genes[1]),
        )
        factories.GeneModuleFactory.create_batch(
            size=4,
            dataset=self.homo_dataset,
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

    @staticmethod
    def create_metacell_links(dataset, metacells):
        for m1, m2 in itertools.combinations(metacells, 2):
            if random.random() < 0.2:
                MetacellLink.objects.create(dataset=dataset, metacell=m1, metacell2=m2)

    def create_metacells(self):
        factories.MetaCellTypeFactory.create_batch(size=9, dataset=self.sponge_dataset)
        factories.MetaCellTypeFactory.create_batch(size=9, dataset=self.homo_dataset)

        factories.MetacellCountFactory.create_batch(size=12, dataset=self.homo_dataset)
        factories.MetacellCountFactory.create_batch(size=18, dataset=self.sponge_dataset)

        sponge_metacells = Metacell.objects.filter(dataset=self.sponge_dataset)
        homo_metacells = Metacell.objects.filter(dataset=self.homo_dataset)
        self.create_metacell_links(self.sponge_dataset, sponge_metacells)
        self.create_metacell_links(self.homo_dataset, homo_metacells)

        sponge_genes = Gene.objects.filter(species=self.sponge)
        homo_genes = Gene.objects.filter(species=self.homo)

        for gene in homo_genes:
            for metacell in homo_metacells:
                factories.MetacellGeneExpressionFactory.create(dataset=self.homo_dataset, gene=gene, metacell=metacell)

        for gene in sponge_genes:
            for metacell in sponge_metacells:
                factories.MetacellGeneExpressionFactory.create(
                    dataset=self.sponge_dataset, gene=gene, metacell=metacell
                )

    def save_HDF_file(self, dataset, species, path):
        with open(path, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(path))
            DatasetFile.objects.get_or_create(
                dataset=dataset, type="singlecell_umifrac", defaults={"file": django_file}
            )

    def create_HDF_file(self, dataset, genes, singlecells):
        output_file = f"{dataset.slug}-singlecell_umifrac.hdf5"
        with h5py.File(output_file, "w") as root:
            root.create_dataset("cell_names", data=singlecells, dtype=h5py.string_dtype())
            num_sc = len(singlecells) // 10
            fake = Faker()
            for gene in genes:
                dataset = np.empty(shape=num_sc, dtype=[("c", np.int32), ("e", np.float32)])
                for j in range(num_sc):
                    position = fake.random_int(min=0, max=len(singlecells) - 1)
                    expression = fake.pyfloat(min_value=0.01, max_value=21.0)
                    dataset[j] = (position, expression)
                root.create_dataset(name=gene, data=dataset)
        return output_file

    def create_expression_files(self):
        homo_singlecells = [sc.name for sc in SingleCell.objects.filter(dataset=self.homo_dataset)]
        homo_genes = [gene.name for gene in Gene.objects.filter(species=self.homo)]
        file1 = self.create_HDF_file(self.homo_dataset, homo_genes, homo_singlecells)
        self.save_HDF_file(self.homo_dataset, self.homo, file1)
        sponge_singlecells = [sc.name for sc in SingleCell.objects.filter(dataset=self.sponge_dataset)]
        sponge_genes = [gene.name for gene in Gene.objects.filter(species=self.sponge)]
        file2 = self.create_HDF_file(self.sponge_dataset, sponge_genes, sponge_singlecells)
        self.save_HDF_file(self.sponge_dataset, self.sponge, file2)

    def create_singlecells(self):
        factories.SingleCellFactory.create_batch(size=100, dataset=self.homo_dataset)
        factories.SingleCellFactory.create_batch(size=120, dataset=self.sponge_dataset)
        self.create_expression_files()
