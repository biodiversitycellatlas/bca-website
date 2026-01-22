import os
from unittest import TestCase

from django.core.files import File as DjangoFile

from app.apps import AppConfig
from app.models import Species, SpeciesFile
from app.systemchecks.files import check_application_files


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
        self.assertEqual(errors, [])
