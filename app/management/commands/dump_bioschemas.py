"""
Dump the Bioschemas JSON-LD served by the Data Portal pages for validation.

Renders pages using Django test client into markup for public structured-data
validators (validator.schema.org, Google's Rich Results Test) that cannot
access local instances.

    # all pages with markup, one summary line per page
    python manage.py dump_bioschemas

    # one page, JSON only: paste into a validator or pipe to pyshacl
    python manage.py dump_bioschemas --raw /atlas/amphimedon-queenslandica-larva/ > dataset.jsonld

    # override the host and scheme used for absolute URLs
    python manage.py dump_bioschemas --host portal-bca-gambusia:8081
    python manage.py dump_bioschemas --host portal.biodiversitycellatlas.org --scheme https

Exits non-zero if a page has no JSON-LD, making it a regression check for
missing markup.
"""

import json

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from app.models import Dataset, Gene, Species
from config.pre_settings import get_env

# Default port per scheme, so `get_host()` omits it from the absolute URLs
DEFAULT_PORTS = {"http": "80", "https": "443"}


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
            metavar="HOST[:PORT]",
            help="Authority for the payload's absolute URLs (default: $DJANGO_HOSTNAME, "
            "plus $WEB_PORT outside production).",
        )
        parser.add_argument(
            "--scheme",
            choices=sorted(DEFAULT_PORTS),
            default=None,
            help="Scheme for the payload's absolute URLs (default: https under ENVIRONMENT=prod, else http).",
        )

    def is_prod(self):
        """Return True when running under the production environment."""
        return get_env("ENVIRONMENT") == "prod"

    def default_scheme(self):
        """
        Return the scheme the deployment is served over.

        `nginx/nginx.prod.conf.template` 301s port 80 to https in production, so a
        payload full of `http://` URLs would advertise the wrong canonical form.
        """
        return "https" if self.is_prod() else "http"

    def default_authority(self):
        """
        Return the ``host[:port]`` the payload's absolute URLs are built from.

        `DJANGO_HOSTNAME` is a *bare* hostname by design: nginx serves it on 443 in
        production, but publishes it on `WEB_PORT` everywhere else, so outside
        production the port has to be added back or the URLs are unreachable.
        """
        host = get_env("DJANGO_HOSTNAME")
        if not host:
            raise CommandError("DJANGO_HOSTNAME is not set: pass --host HOST[:PORT] instead.")

        if ":" in host or self.is_prod():
            return host

        port = get_env("WEB_PORT")
        return f"{host}:{port}" if port else host

    def request_kwargs(self, authority, scheme):
        """
        Translate a ``host[:port]`` authority into test-client request overrides.

        These belong on each request rather than on the client: Django's
        `RequestFactory.generic()` resets `SERVER_PORT` and `wsgi.url_scheme` from
        its own `secure` flag *after* the client defaults have been applied, so
        passing them to `Client(...)` silently has no effect.
        """
        host, _, port = authority.partition(":")
        return {
            "SERVER_NAME": host,
            "SERVER_PORT": port or DEFAULT_PORTS[scheme],
            "secure": scheme == "https",
        }

    def default_urls(self):
        """Return one representative URL per page type that carries markup."""
        species = Species.objects.filter(genes__isnull=False).distinct().first()
        dataset = Dataset.objects.filter(species=species).first()
        gene = Gene.objects.filter(species=species).first()

        urls = [
            reverse("index"),
            reverse("downloads"),
            reverse("species_entry"),
            reverse("dataset_entry"),
        ]
        if species:
            # Species detail matches on `scientific_name`, not the slug, so take the
            # URL from the model rather than assembling it from the slug.
            urls += [
                species.get_absolute_url(),
                reverse("gene_entry", args=[species.slug]),
            ]
        if gene:
            urls.append(gene.get_absolute_url())
        if dataset:
            urls.append(dataset.get_absolute_url())
            if gene:
                urls.append(dataset.get_gene_url(gene.name))
        return urls

    def describe(self, payload):
        """Return a one-line summary of a payload's type and profile claim."""
        profile = payload.get("dct:conformsTo", {}).get("@id", "no profile")
        return f"{payload['@type']} <- {profile}"

    def jsonld_scripts(self, html):
        """Return the JSON-LD ``<script>`` tags found in `html`."""
        return BeautifulSoup(html, "html.parser").find_all("script", type="application/ld+json")

    def handle(self, *args, **options):
        """Render each URL and write out the JSON-LD blocks it serves."""
        raw = options["raw"]
        # Resolved here rather than as argparse defaults so the environment is
        # read at run time, not at parser construction.
        scheme = options["scheme"] or self.default_scheme()
        authority = options["host"] or self.default_authority()
        request = self.request_kwargs(authority, scheme)
        client = Client()

        # The test client sends its own Host header, which ALLOWED_HOSTS rejects
        # under ENVIRONMENT=prod.
        with override_settings(ALLOWED_HOSTS=["*"]):
            urls = options["urls"] or self.default_urls()
            missing = []
            all_payloads = []

            for url in urls:
                response = client.get(url, **request)
                scripts = self.jsonld_scripts(response.content) if response.status_code == 200 else []
                # Parse before printing so a malformed payload fails here rather
                # than silently in whatever consumes the output.
                payloads = [json.loads(script.string) for script in scripts]

                if not raw:
                    summary = ", ".join(self.describe(each) for each in payloads) or "NO JSON-LD"
                    self.stdout.write(f"\n{'=' * 78}")
                    self.stdout.write(f"{url}  [HTTP {response.status_code}]  {summary}")
                    self.stdout.write("=" * 78)

                if not payloads:
                    missing.append(f"{url} (HTTP {response.status_code})")
                    continue

                all_payloads += payloads

                if not raw:
                    for payload in payloads:
                        self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))

        if raw:
            # A single payload is printed bare; more than one is wrapped in an
            # array, since multiple bare top-level objects back-to-back would
            # not be valid JSON on their own.
            if len(all_payloads) == 1:
                self.stdout.write(json.dumps(all_payloads[0], indent=2, ensure_ascii=False))
            elif all_payloads:
                self.stdout.write(json.dumps(all_payloads, indent=2, ensure_ascii=False))

        if not raw:
            self.stdout.write(f"\n{len(urls) - len(missing)}/{len(urls)} pages served JSON-LD.")

        if missing:
            raise CommandError("No JSON-LD served by: " + ", ".join(missing))
