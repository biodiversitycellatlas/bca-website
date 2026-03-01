import os
import tempfile

from django.core.files import File as DjangoFile
from django.test import TestCase, override_settings

from app.apps import AppConfig
from app.models import Species, SpeciesFile, Dataset, Gene, MetacellType, Metacell, MetacellGeneExpression
from app.systemchecks.files import check_application_files
from app.systemchecks.metacellgenexpression import check_negative_umis
from app.systemchecks.postgresql_tables import check_tables


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FilesSystemCheckTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(
            common_name="fileschecker", scientific_name="FileCheckerSp", description="F C Species"
        )
        test_file = os.path.join(os.path.dirname(__file__), "test_fixtures", "test-dmd-db.dmnd")
        with open(test_file, "rb") as f:
            django_file = DjangoFile(f, name=os.path.basename(test_file))
            SpeciesFile.objects.get_or_create(species=species1, type="DIAMOND", defaults={"file": django_file})

    def test_execution(self):
        errors = check_application_files([AppConfig], deploy=True)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "bca.E001")


class MetacellGeneExpressionCheckTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        species1 = Species.objects.create(
            common_name="metacellgeneexpcheck",
            scientific_name="metacellgeneexpcheck",
            description="metacellgeneexpcheck Species",
        )
        dataset1 = Dataset.objects.create(species=species1, name="mcgecheckdataset", description="mcgecheckdataset")
        gene1 = Gene.objects.create(species=species1, name="gene1", description="gene1")
        type1 = MetacellType.objects.create(name="type1", dataset=dataset1)
        meta1 = Metacell.objects.create(name="meta1", dataset=dataset1, type=type1, x=1, y=1)
        MetacellGeneExpression.objects.create(
            dataset=dataset1, gene=gene1, metacell=meta1, umi_raw=-1, umifrac=1.41, fold_change=4
        )

    def test_execution(self):
        errors = check_negative_umis([AppConfig], deploy=True)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "bca.E002")


class PostgresTablesCheckTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        speciesP = Species.objects.create(
            common_name="postgrescheck",
            scientific_name="postgrescheck",
            description="postgrescheck Species",
        )
        dataset1 = speciesP.datasets.create(name="psqlcheckdataset", description="psqlcheckdataset")
        gene1 = speciesP.genes.create(name="geneP", description="geneP")
        gm = dataset1.gene_modules.create(name="psql")
        gm.membership.create(membership_score=4.1, gene=gene1)

    # In test mode there are several empty tables.
    # Looking only for table 'genemodule':
    def test_execution(self):
        errors = check_tables([AppConfig], deploy=True)
        for error in errors:
            if error.obj == "genemodule":
                self.assertEqual(error.id, "bca.E003")
