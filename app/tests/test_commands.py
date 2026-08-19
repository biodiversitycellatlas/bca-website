import json
import os
import tempfile
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.management.commands import dump_bioschemas
from app.tests.test_utils import assert_conforms
from app.tests.views.utils import DataTestCase


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CreateTestDBTest(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command("createtestdb", stdout=out)
        self.assertIn("Successfully created Test Database", out.getvalue())


class DumpBioschemasCommandTest(DataTestCase):
    def test_dump_command_reports_every_page(self):
        """`dump_bioschemas` is the paste-into-a-validator helper (see the report, §8.3)."""
        out = StringIO()
        call_command("dump_bioschemas", stdout=out)
        output = out.getvalue()

        assert "NO JSON-LD" not in output
        assert "pages served JSON-LD." in output
        for profile in ("Taxon/1.0-RELEASE", "Gene/1.0-RELEASE", "Dataset/1.0-RELEASE"):
            assert profile in output, f"no page reported {profile}"

    def test_dump_command_raw_mode_emits_only_json(self):
        out = StringIO()
        call_command("dump_bioschemas", f"/atlas/{self.adult_mouse.slug}/", "--raw", stdout=out)
        payload = json.loads(out.getvalue())
        assert_conforms(payload, "Dataset")

    def test_dump_command_raw_mode_wraps_multiple_payloads_in_an_array(self):
        """Several URLs (or a page with several blocks) must still parse as one JSON document."""
        out = StringIO()
        call_command(
            "dump_bioschemas",
            f"/atlas/{self.adult_mouse.slug}/",
            "/entry/species/",
            "--raw",
            stdout=out,
        )
        payloads = json.loads(out.getvalue())
        assert isinstance(payloads, list)
        assert {each["@type"] for each in payloads} == {"Dataset", "CollectionPage"}

    def dumped_url(self, env, *args):
        """Return the `url` of the payload dumped for a gene page under `env`."""
        url = f"/entry/gene/{self.mouse.slug}/{self.brca1.name}/"
        out = StringIO()
        with mock.patch.dict(os.environ, env, clear=True):
            call_command("dump_bioschemas", url, "--raw", *args, stdout=out)
        return json.loads(out.getvalue())["url"], url

    def test_dump_command_builds_urls_from_django_hostname(self):
        """`DJANGO_HOSTNAME` is set in every environment, so it is the natural default."""
        built, url = self.dumped_url({"DJANGO_HOSTNAME": "portal.example.org"})
        assert built == f"http://portal.example.org{url}"

    def test_dump_command_adds_web_port_outside_production(self):
        """`DJANGO_HOSTNAME` is a bare hostname, but dev nginx publishes on WEB_PORT."""
        built, url = self.dumped_url({"DJANGO_HOSTNAME": "portal-bca-gambusia", "WEB_PORT": "8081"})
        assert built == f"http://portal-bca-gambusia:8081{url}"

    def test_dump_command_omits_web_port_in_production(self):
        """Production nginx serves DJANGO_HOSTNAME on 443, so no port belongs in the URL."""
        env = {"DJANGO_HOSTNAME": "portal.example.org", "WEB_PORT": "8081", "ENVIRONMENT": "prod"}
        built, url = self.dumped_url(env)
        assert built == f"https://portal.example.org{url}"

    def test_dump_command_host_option_overrides_the_environment(self):
        env = {"DJANGO_HOSTNAME": "portal.example.org", "WEB_PORT": "8081"}
        built, url = self.dumped_url(env, "--host", "portal-bca-gambusia:8000")
        assert built == f"http://portal-bca-gambusia:8000{url}"

    def test_dump_command_scheme_option_overrides_the_environment(self):
        built, url = self.dumped_url({"DJANGO_HOSTNAME": "portal.example.org"}, "--scheme", "https")
        assert built == f"https://portal.example.org{url}"

    def test_dump_command_falls_back_without_django_hostname(self):
        built, url = self.dumped_url({})
        assert built == f"http://{dump_bioschemas.FALLBACK_HOST}{url}"

    def test_dump_command_fails_when_a_page_serves_nothing(self):
        """Non-zero exit makes it usable as a CI check that markup has not vanished."""
        with pytest.raises(CommandError, match="No JSON-LD served by"):
            call_command("dump_bioschemas", "/about/", stdout=StringIO())
