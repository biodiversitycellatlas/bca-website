import tempfile
from io import StringIO
from django.core.management import call_command
from django.test import TestCase, override_settings

@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CreateTestDBTest(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command("createtestdb", stdout=out)
        self.assertIn("Successfully created Test Database", out.getvalue())
