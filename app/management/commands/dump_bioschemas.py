"""
Dump the Bioschemas JSON-LD served by the portal's pages.

Renders pages through Django's test client, so no server, host entry or public
URL is involved. That matters because the public structured-data validators
(validator.schema.org, Google's Rich Results Test) fetch a URL from *their*
servers and cannot reach a local instance -- but both accept pasted markup, and
this command produces exactly that.

    # every page that carries markup, with a summary line per page
    python manage.py dump_bioschemas

    # one page, JSON only, ready to paste into a validator or pipe to pyshacl
    python manage.py dump_bioschemas --raw /entry/domain/1/ > domain.jsonld

    # override the host the payload's absolute URLs are built from
    python manage.py dump_bioschemas --host portal.biodiversitycellatlas.org

The command exits non-zero when a page serves no JSON-LD, so it doubles as a
regression check that the markup has not silently disappeared.
"""

import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.test.utils import override_settings

from app.models import Dataset, Domain, Gene, Species
from config.pre_settings import get_env

JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)

# Absolute URLs in the payload are built from the request host, so it defaults to
# the host this deployment is served under. `DJANGO_HOSTNAME` is already set in
# every environment (see `.env.template`); the fallback only applies when the
# command is run outside the compose stack.
FALLBACK_HOST = "portal.biodiversitycellatlas.org"


def default_host():
    """Return the host used to build absolute URLs in the payload."""
    return get_env("DJANGO_HOSTNAME", FALLBACK_HOST)


def default_urls():
    """Return one representative URL per page type that carries markup."""
    species = Species.objects.filter(genes__isnull=False).distinct().first()
    dataset = Dataset.objects.filter(species=species).first()
    gene = Gene.objects.filter(species=species).first()
    domain = Domain.objects.filter(gene__isnull=False).distinct().first()

    urls = ["/", "/downloads/", "/entry/species/", "/entry/dataset/", "/entry/domain/"]
    if species:
        # Species detail matches on `scientific_name`, not the slug, so take the
        # URL from the model rather than assembling it from the slug.
        urls += [species.get_absolute_url(), f"/entry/gene/{species.slug}/"]
    if gene:
        urls.append(gene.get_absolute_url())
    if domain:
        urls.append(domain.get_absolute_url())
    if dataset:
        urls.append(dataset.get_absolute_url())
        if gene:
            urls.append(dataset.get_gene_url(gene.name))
    return urls


class Command(BaseCommand):
    """Dump the Bioschemas JSON-LD embedded in the portal's pages."""

    help = "Dump the Bioschemas JSON-LD served by the portal's pages."

    def add_arguments(self, parser):
        """Register command arguments."""
        parser.add_argument(
            "urls",
            nargs="*",
            help="Paths to render. Defaults to one representative URL per page type.",
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Print only JSON, no headers, so the output is a valid file on its own.",
        )
        parser.add_argument(
            "--host",
            default=None,
            help="Host used to build absolute URLs in the payload (default: $DJANGO_HOSTNAME).",
        )

    def describe(self, payload):
        """Return a one-line summary of a payload's type and profile claim."""
        profile = payload.get("dct:conformsTo", {}).get("@id", "no profile")
        return f"{payload['@type']} <- {profile}"

    def handle(self, *args, **options):
        """Render each URL and write out the JSON-LD blocks it serves."""
        raw = options["raw"]
        # Resolved here rather than as an argparse default so the environment is
        # read at run time, not at parser construction.
        client = Client(SERVER_NAME=options["host"] or default_host())

        # The test client sends its own Host header, which ALLOWED_HOSTS rejects
        # under ENVIRONMENT=prod.
        with override_settings(ALLOWED_HOSTS=["*"]):
            urls = options["urls"] or default_urls()
            missing = []

            for url in urls:
                response = client.get(url)
                blocks = JSONLD.findall(response.content.decode()) if response.status_code == 200 else []
                # Parse before printing so a malformed payload fails here rather
                # than silently in whatever consumes the output.
                payloads = [json.loads(block) for block in blocks]

                if not raw:
                    summary = ", ".join(self.describe(each) for each in payloads) or "NO JSON-LD"
                    self.stdout.write(f"\n{'=' * 78}")
                    self.stdout.write(f"{url}  [HTTP {response.status_code}]  {summary}")
                    self.stdout.write("=" * 78)

                if not payloads:
                    missing.append(f"{url} (HTTP {response.status_code})")
                    continue

                for payload in payloads:
                    self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))

        if not raw:
            self.stdout.write(f"\n{len(urls) - len(missing)}/{len(urls)} pages served JSON-LD.")

        if missing:
            raise CommandError("No JSON-LD served by: " + ", ".join(missing))
