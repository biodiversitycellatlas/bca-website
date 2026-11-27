"""Populate Dataset publications from DOI metadata."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import re
import urllib.request

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import strip_tags

from app.models import Dataset, Publication


CROSSREF_URL = "https://api.crossref.org/works/"
DATACITE_URL = "https://api.datacite.org/dois/"
NCBI_ESearch_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

USER_AGENT = "BCA/1.0 (mailto:bca@biodiversitycellatlas.org)"
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)

class Command(BaseCommand):
    """Populate Dataset publications from DOI metadata."""

    help = "Add DOI metadata to datasets."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("--config", type=Path, help="YAML file mapping dataset internal IDs to DOIs.")
        parser.add_argument("--replace", action="store_true", help="Replace existing dataset publications.")

    def handle(self, *args, **options):
        """Run the command."""
        doi_map = self.load_yaml(options.get("config"))

        datasets = Dataset.objects.all()
        total = datasets.count()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Processing {total} dataset{'s' if total != 1 else ''}..."))

        for index, dataset in enumerate(datasets, start=1):
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO(f"[{index}/{total}] {dataset.internal_id}: {dataset}"))

            # Dataset already has a publication/DOI.
            if dataset.publication and dataset.publication.doi and not options.get("replace"):
                self.stdout.write(self.style.WARNING(f"  Skipping — DOI already set: {dataset.publication.doi}"))
                continue

            # Get DOI from YAML or ask interactively.
            doi = doi_map.get(str(dataset.internal_id))

            if doi:
                self.stdout.write(f"  DOI from config file: {doi}")
            else:
                doi = self.ask_for_doi(dataset)

            if not doi:
                self.stdout.write(self.style.WARNING("  Skipping — no DOI provided."))
                continue

            try:
                doi = self.normalize_doi(doi)
            except CommandError as exc:
                self.stdout.write(self.style.WARNING(f"  {exc}"))
                doi = self.ask_for_doi(dataset)

                if not doi:
                    self.stdout.write(self.style.WARNING("  Skipping — no DOI provided."))
                    continue

                doi = self.normalize_doi(doi)

            try:
                metadata = self.fetch_metadata(doi)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  Failed to fetch DOI metadata: {exc}"))
                continue

            try:
                publication = self.create_publication(metadata, doi)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  Failed to create publication: {exc}"))
                continue

            dataset.publication = publication
            dataset.save(update_fields=["publication", "date_updated"])
            self.stdout.write(self.style.SUCCESS(f"  Added publication: {publication.title}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))

    def load_yaml(self, path: Path | None) -> dict[str, str]:
        """Load dataset internal ID -> DOI mappings from YAML."""
        if path is None:
            return {}

        if not path.exists():
            raise CommandError(f"YAML file does not exist: {path}")

        try:
            with path.open() as handle:
                data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            raise CommandError(f"Invalid YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise CommandError("YAML must contain a key-value mapping.")

        return { str(dataset_id): str(doi).strip() for dataset_id, doi in data.items() if doi }

    def ask_for_doi(self, dataset: Dataset) -> str | None:
        """Ask interactively for a DOI."""
        label = dataset.get_label()

        try:
            value = input(f"  DOI or paper URL for {label} [Enter to skip]: ").strip()
        except (EOFError, KeyboardInterrupt):
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Input interrupted."))
            raise CommandError("Command interrupted.")

        return value or None


    def find_pubmed_doi(self, pmid: str) -> str | None:
        """Get DOI from PubMed."""
        params = urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "xml"})
        url = f"{NCBI_ESearch_URL.replace('esearch', 'efetch')}?{params}"

        try:
            xml = self.http_get(url)
        except CommandError:
            return None

        match = re.search(r'<ArticleId IdType="doi">([^<]+)</ArticleId>', xml, re.IGNORECASE)
        return match.group(1) if match else None


    def find_doi_from_url(self, url: str) -> str | None:
        """Extract DOI from a paper webpage."""
        parsed = urllib.parse.urlparse(url)

        if parsed.netloc.lower().startswith("pubmed"):
            pmid = parsed.path.strip("/").split("/")[0]
            return self.find_pubmed_doi(pmid)

        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError:
            return None

        match = DOI_PATTERN.search(html)
        return match.group(0).rstrip(".,;:)/\"'") if match else None


    def normalize_doi(self, value: str) -> str:
        """Normalize a DOI or extract one from a paper URL."""
        value = value.strip()

        match = DOI_PATTERN.search(value)
        if match:
            return match.group(0).rstrip(".,;:)")

        if value.startswith(("http://", "https://")):
            doi = self.find_doi_from_url(value)
            if doi:
                return doi

            raise CommandError(f"Could not find DOI on {value}")

        return value.rstrip("/").strip()


    def clean_title(self, title: str) -> str:
        """Convert metadata title to clean plain text."""
        # Avoid HTML tags
        title = strip_tags(title)
        return re.sub(r"\s+", " ", title).strip()


    def fetch_metadata(self, doi: str) -> dict:
        """Fetch metadata from Crossref, falling back to DataCite."""
        encoded_doi = urllib.parse.quote(doi, safe="")

        try:
            response = self.http_get(f"{CROSSREF_URL}{encoded_doi}")
            data = json.loads(response)
            return self.crossref_to_metadata(data["message"])
        except Exception as crossref_error:
            self.stdout.write(self.style.WARNING(f"  Crossref lookup failed, trying DataCite..."))

            try:
                response = self.http_get(f"{DATACITE_URL}{encoded_doi}")
                data = json.loads(response)
                return self.datacite_to_metadata(data["data"]["attributes"])
            except Exception as datacite_error:
                raise CommandError(
                    f"Crossref: {crossref_error}; "
                    f"DataCite: {datacite_error}"
                ) from datacite_error

    def http_get(self, url: str) -> str:
        """Perform a GET request."""
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise CommandError(f"HTTP {exc.code} while requesting {url}") from exc
        except urllib.error.URLError as exc:
            raise CommandError(f"Could not connect to metadata API: {exc.reason}") from exc

    def crossref_to_metadata(self, data: dict) -> dict:
        """Convert Crossref metadata to our internal representation."""
        title = self.clean_title(self.first_value(data.get("title")))

        authors = []
        for author in data.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = " ".join(part for part in (given, family) if part).strip()

            if name:
                authors.append(name)

        year = self.extract_year(data)
        journal = self.first_value(data.get("container-title")) or data.get("publisher", "")
        pmid = self.lookup_pmid(data.get("DOI"))

        if not title:
            raise CommandError("DOI metadata contains no title.")

        return { "title": title, "authors": ", ".join(authors), "year": year, "journal": journal, "pmid": pmid }

    def datacite_to_metadata(self, data: dict) -> dict:
        """Convert DataCite metadata to our internal representation."""
        title = self.clean_title(self.first_value(data.get("titles", []), key="title"))

        authors = []
        for creator in data.get("creators", []):
            name = (
                creator.get("name")
                or " ".join(part for part in (creator.get("givenName"), creator.get("familyName")) if part)
            )

            if name:
                authors.append(name)

        year = data.get("publicationYear") or data.get("created", "")[:4]

        journal = ""
        for container in data.get("container", []) if isinstance(
            data.get("container"), list
        ) else []:
            journal = container.get("title", "")
            if journal:
                break

        doi = data.get("doi")
        pmid = self.lookup_pmid(doi)

        if not title:
            raise CommandError("DOI metadata contains no title.")

        journal = journal or "Unknown"
        return { "title": title, "authors": ", ".join(authors), "year": int(year), "journal": journal, "pmid": pmid }

    def create_publication(self, metadata: dict, doi: str) -> Publication:
        """Create or reuse a Publication."""
        pmid = metadata["pmid"]

        if not pmid:
            raise CommandError("Could not find the required PMID for this DOI.")

        publication = Publication.objects.filter(doi=doi).first()

        if publication:
            self.stdout.write(self.style.WARNING(f"  Publication already exists for DOI {doi}; reusing it."))
            return publication

        existing_pmid = Publication.objects.filter(pmid=pmid).first()
        if existing_pmid:
            self.stdout.write(self.style.WARNING(f"  PMID {pmid} already exists; reusing existing publication."))
            return existing_pmid

        with transaction.atomic():
            return Publication.objects.create(
                title=metadata["title"][:500],
                authors=metadata["authors"],
                year=metadata["year"],
                journal=metadata["journal"][:255],
                doi=doi,
                pmid=pmid,
            )

    def lookup_pmid(self, doi: str | None) -> str | None:
        """Look up PMID from DOI using NCBI E-utilities."""
        if not doi:
            return None

        query = urllib.parse.quote(f"{doi}[DOI]")
        url = f"{NCBI_ESearch_URL}?db=pubmed&term={query}&retmode=json"

        try:
            response = self.http_get(url)
            data = json.loads(response)
            ids = data.get("esearchresult", {}).get("idlist", [])

            return ids[0] if ids else None
        except Exception:
            return None

    @staticmethod
    def first_value(values, key=None):
        """Return the first value from a metadata list."""
        if not values:
            return ""

        value = values[0]

        if key:
            if isinstance(value, dict):
                return value.get(key, "")
            return ""

        return value

    @staticmethod
    def extract_year(data: dict) -> int:
        """Extract publication year from Crossref metadata."""
        for field in ("published-print", "published-online", "published", "issued", "created"):
            date = data.get(field, {})
            parts = date.get("date-parts", [])

            if parts and parts[0]:
                return int(parts[0][0])

        raise CommandError("DOI metadata contains no publication year.")
