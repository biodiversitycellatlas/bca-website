"""Utilities for tests."""

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile

from app.models import Species, Domain, GeneList


class DataTestCase(TestCase):
    @classmethod
    def setup_datasets(cls):
        # Create mouse datasets
        cls.mouse = Species.objects.create(scientific_name="Mus musculus", common_name="mouse")
        cls.adult_mouse = cls.mouse.datasets.create(name="adult")
        cls.baby_mouse = cls.mouse.datasets.create(name="baby")

        # Create human dataset with no name
        cls.human = Species.objects.create(scientific_name="Homo sapiens", common_name="human")
        cls.human.datasets.create()

    @classmethod
    def setup_genes(cls):
        cls.brca1 = cls.mouse.genes.create(name="Brca1")
        cls.brca2 = cls.mouse.genes.create(name="Brca2")

        # Add protein domains
        cls.brca1_domains = [Domain.objects.create(name=n) for n in ["BRCA1_C", "BRCT", "COBRA1"]]
        cls.brca1.domains.add(*cls.brca1_domains)

        cls.brca2_domains = [Domain.objects.create(name=n) for n in ["BRCA2_TR2", "BRCA-2_helical", "BRCA-2_OB3"]]
        cls.brca2.domains.add(*cls.brca2_domains)

        # Add gene modules
        cls.gene_module = cls.brca1.modules.create(dataset=cls.adult_mouse, name="blue", membership_score="0.92")
        cls.brca2.modules.create(dataset=cls.adult_mouse, name="green", membership_score="0.65")

        # Add gene list
        cls.gene_list = GeneList.objects.create(name="BRCA genes", description="BRCA-associated genes")
        cls.gene_list.genes.add(cls.brca1, cls.brca2)

        # Add orthologs
        cls.brca1_human = cls.human.genes.create(name="BRCA1")
        cls.human.orthologs.create(orthogroup="OG1", gene=cls.brca1_human)
        cls.mouse.orthologs.create(orthogroup="OG1", gene=cls.brca1)

    @classmethod
    def setup_fasta(cls):
        # Add FASTA file
        fasta_demo = ">Brca1\nMACDEFGHIK\nLMNPQRSTVW\n>Brca2\nMACDEFGHIK\n".encode("utf-8")
        cls.mouse_fasta = cls.mouse.files.create(type="Proteome", file=SimpleUploadedFile("demo.fasta", fasta_demo))

    @classmethod
    def setUpTestData(cls):
        # Runs once per class
        cls.setup_datasets()
        cls.setup_genes()
        cls.setup_fasta()

        # Prepare client
        cls.client = Client()
