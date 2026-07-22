import itertools
import os
import random
import subprocess
from typing import TextIO

import factory.random
import h5py
import numpy as np
from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand
from django.db import connection
from faker import Faker

from app.management.commands import factories
from app.models import (
    Species,
    Dataset,
    Domain,
    Publication,
    GeneList,
    Gene,
    GeneModuleMembership,
    Metacell,
    MetacellLink,
    SingleCell,
    Source,
    DatasetFile,
    QualityControl,
    DatasetQualityControl,
    DBVersion,
    MetacellType,
    MetacellTypeSimilarity,
    GeneCorrelation,
    GeneModule,
    GeneModuleEigengene,
    Meta,
    SpeciesFile,
)


def setup_test_environment():
    factory.random.reseed_random("bca_project")


def create_tgrm_extension():
    """Installs the pg_trm search extension"""
    with connection.cursor() as cursor:
        cursor.execute("create extension pg_trgm;")


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
        self.fake = Faker()
        self.sponge = None
        self.homo = None
        self.sponge_dataset = None
        self.homo_dataset = None

    def handle(self, *args, **options):
        """
        Database creation
        """
        setup_test_environment()
        create_tgrm_extension()
        self.create_datasets()
        self.create_metadata()
        self.create_genes()
        self.create_gene_modules()
        self.create_orthogroups()
        self.create_metacells()
        self.create_singlecells()
        self.create_quality_data()
        self.create_metacell_type_similarity()
        self.create_all_genecorrelations()
        self.create_all_eigengene_values()
        self.create_species_files()
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

        homo_pub = Publication.objects.create(
            title="Human Atlas",
            authors="James Gunn",
            year=2024,
            journal="Nature",
            pmid=13054699,
            doi="10.1038/171737a0",
        )

        sponge_pub = Publication.objects.create(
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
            publication=homo_pub,
            order=0,
        )

        self.sponge_dataset = Dataset.objects.create(
            species=self.sponge,
            name=None,
            description="random sponge",
            image_url="https://upload.wikimedia.org/wikipedia/commons/b/b4/Amphimedon_queenslandica_adult.png",
            publication=sponge_pub,
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

        for gmm in GeneModuleMembership.objects.all():
            score = self.fake.pyfloat(left_digits=1, right_digits=3, min_value=0.001, max_value=1.0)
            gmm.membership_score = score
            gmm.save()

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

    @staticmethod
    def save_hdf5_file(dataset, path):
        with open(path, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(path))
            DatasetFile.objects.get_or_create(
                dataset=dataset, type="singlecell_umifrac", defaults={"file": django_file}
            )

    def create_hdf5_file(self, dataset, genes, singlecells):
        output_file = f"{dataset.slug}-singlecell_umifrac.hdf5"
        with h5py.File(output_file, "w") as root:
            root.create_dataset("cell_names", data=singlecells, dtype=h5py.string_dtype())
            num_sc = len(singlecells) // 10
            for gene in genes:
                data = np.empty(shape=num_sc, dtype=[("c", np.int32), ("e", np.float32)])
                for j in range(num_sc):
                    position = self.fake.random_int(min=0, max=len(singlecells) - 1)
                    expression = self.fake.pyfloat(min_value=0.01, max_value=21.0)
                    data[j] = (position, expression)
                root.create_dataset(name=gene, data=data)
        self.save_hdf5_file(dataset, output_file)

    def create_expression_files(self):
        homo_singlecells = [sc.name for sc in SingleCell.objects.filter(dataset=self.homo_dataset)]
        homo_genes = [gene.name for gene in Gene.objects.filter(species=self.homo)]
        self.create_hdf5_file(self.homo_dataset, homo_genes, homo_singlecells)

        sponge_singlecells = [sc.name for sc in SingleCell.objects.filter(dataset=self.sponge_dataset)]
        sponge_genes = [gene.name for gene in Gene.objects.filter(species=self.sponge)]
        self.create_hdf5_file(self.sponge_dataset, sponge_genes, sponge_singlecells)

    def create_singlecells(self):
        factories.SingleCellFactory.create_batch(size=100, dataset=self.homo_dataset)
        factories.SingleCellFactory.create_batch(size=120, dataset=self.sponge_dataset)
        self.create_expression_files()

    def create_quality_data(self):

        qc = QualityControl.objects.create(type="Cell metrics", name="Number of cells", description="Number of cells")
        DatasetQualityControl.objects.create(
            metric=qc, value=self.fake.random_int(min=2001, max=30153), dataset=self.homo_dataset
        )
        DatasetQualityControl.objects.create(
            metric=qc, value=self.fake.random_int(min=2001, max=30153), dataset=self.sponge_dataset
        )

    def create_metadata(self):
        DBVersion.objects.create(
            version="e2e_db",
            description="Data Base for e2e tests",
            populated_at=self.fake.date_this_month(),
            commit="e2e tests",
        )
        ncbi = Source.objects.create(
            name="NCBI Taxonomy",
            description="NCBI Taxonomy Database",
            url="https://www.ncbi.nlm.nih.gov/",
            query_url="https://www.ncbi.nlm.nih.gov/datasets/taxonomy/{{id}}",
        )

        Meta.objects.create(species=self.homo, key="taxon_id", value="9606", source=ncbi, query_term="9606")
        Meta.objects.create(species=self.sponge, key="taxon_id", value="400682", source=ncbi, query_term="400682")
        Meta.objects.create(species=self.homo, key="phylum", value="Chordata", source=ncbi, query_term="7711")
        Meta.objects.create(species=self.sponge, key="phylum", value="Porifera", source=ncbi, query_term="6040")

    def create_metacell_type_similarity(self):
        metacelltypes = MetacellType.objects.all()
        for t1, t2 in itertools.combinations(metacelltypes, 2):
            MetacellTypeSimilarity.objects.create(
                metacelltype=t1,
                metacelltype2=t2,
                samap_score=self.fake.pyfloat(left_digits=2, right_digits=2, min_value=0.01, max_value=1),
            )

    def create_genecorrelations(self, species, dataset):
        genes = Gene.objects.filter(species=species)
        for g1, g2 in itertools.combinations(genes, 2):
            GeneCorrelation.objects.create(
                gene=g1,
                gene2=g2,
                dataset=dataset,
                pearson=self.fake.pyfloat(left_digits=2, right_digits=2, min_value=0.01, max_value=1.0),
                spearman=self.fake.pyfloat(left_digits=2, right_digits=2, min_value=0.01, max_value=1.0),
            )

    def create_all_genecorrelations(self):
        self.create_genecorrelations(self.sponge, self.sponge_dataset)
        self.create_genecorrelations(self.homo, self.homo_dataset)

    def create_eigengene_values(self, dataset):
        modules = GeneModule.objects.filter(dataset=dataset)
        metacells = Metacell.objects.filter(dataset=dataset)
        for metacell in metacells:
            for module in modules:
                GeneModuleEigengene.objects.create(
                    module=module,
                    metacell=metacell,
                    eigengene_value=self.fake.pyfloat(left_digits=2, right_digits=3, min_value=0.01, max_value=1.0),
                )

    def create_all_eigengene_values(self):
        self.create_eigengene_values(self.sponge_dataset)
        self.create_eigengene_values(self.homo_dataset)

    @staticmethod
    def save_species_file(species, kind, path):
        with open(path, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(path))
            SpeciesFile.objects.get_or_create(species=species, type=kind, defaults={"file": django_file})

    def create_fasta_file(self, species, genes):
        output_file = f"{species} - Proteome.fasta"
        with open(output_file, "w") as f:
            for gene in genes:
                sequence = self.fake.bothify(
                    text="M????????????????????????????????????????", letters="ACDEFGHIKLMNPQRSTVWY"
                )
                f.write(f">{gene}\n")
                f.write(sequence)
                f.write("\n")
        self.save_species_file(species, "Proteome", output_file)
        return output_file

    def create_diamond_database(self, species, input_file, output_file):
        result = subprocess.run(
            ["/usr/bin/diamond", "makedb", "--in", input_file, "--db", output_file], capture_output=True, text=True
        )
        if result.returncode == 0:
            self.save_species_file(species, "DIAMOND", output_file)

    def create_species_files(self):
        sponge_genes = list(self.sponge.genes.values_list("name", flat=True))
        input_file = self.create_fasta_file(self.sponge, sponge_genes)
        output_file = f"{self.sponge.scientific_name} - DIAMOND.dmnd"
        self.create_diamond_database(self.sponge, input_file, output_file)

        homo_genes = list(self.homo.genes.values_list("name", flat=True))
        input_file = self.create_fasta_file(self.homo, homo_genes)
        output_file = f"{self.homo.scientific_name} - DIAMOND.dmnd"
        self.create_diamond_database(self.homo, input_file, output_file)
