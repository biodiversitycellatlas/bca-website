from unittest import TestCase

from app.apps import AppConfig
from app.systemchecks.files import check_application_files


class FilesSystemCheckTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def test_execution(self):
        check_application_files([AppConfig], deploy=True)
