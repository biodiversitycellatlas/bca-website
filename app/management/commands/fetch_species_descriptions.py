import json
import time
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from app.models import Species

USER_AGENT = "BCA-Portal/1.0"
THROTTLE = 0.3  # seconds
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIPEDIA_TITLE_OVERRIDES = {
    "Xenia sp.": "Xenia (coral)",
}

class Command(BaseCommand):
    help = "Store species descriptions from Wikipedia."

    def fetch_species_description(self, scientific_name):
        title = WIKIPEDIA_TITLE_OVERRIDES.get(scientific_name, scientific_name)
        title = urllib.parse.quote(title.replace(" ", "_"))
        url = WIKIPEDIA_SUMMARY_URL.format(title=title)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(req) as response:
                data = json.load(response)

            description = data.get("extract_html")
            wikipedia_url = data.get("content_urls", {}).get("desktop", {}).get("page")

            # Remove paragraph tags
            description = description.replace("<p>", "").replace("</p>", "")

            # Append Wikipedia link
            description += (
                f' <a class="float-end" href="{wikipedia_url}" target="_blank" rel="noopener noreferrer">Wikipedia</a>'
            )
            return description
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None

    def add_arguments(self, parser):
        parser.add_argument("species", nargs="*", type=str, help="Scientific names of species to fetch.")
        parser.add_argument("--force", action="store_true", help="Overwrite existing descriptions.")

    def handle(self, *args, **options):
        force = options["force"]
        species_names = options["species"]

        if species_names:
            species_list = Species.objects.filter(scientific_name__in=species_names)
        else:
            species_list = Species.objects.all()
        species_list = list(species_list)

        # Warn about given species missing from database
        found_names = {species.scientific_name for species in species_list}
        for name in species_names:
            if name not in found_names:
                self.stderr.write(self.style.ERROR(f"Species '{name}' not found."))

        updated = 0
        skipped = 0
        not_found = 0

        for species in species_list:
            if species.description and not force:
                self.stdout.write(f"  {species.scientific_name}: already has description, skipping...")
                skipped += 1
                continue

            description = self.fetch_species_description(species.scientific_name)
            if description:
                species.description = description
                species.save(update_fields=["description"])
                self.stdout.write(self.style.SUCCESS(f"  ✓ {species.scientific_name}: updated"))
                updated += 1
            else:
                self.stderr.write(self.style.WARNING(f"  ✗ {species.scientific_name}: no Wikipedia page found"))
                not_found += 1

            time.sleep(THROTTLE)

        self.stdout.write(self.style.SUCCESS(f"\nDone: {updated} updated, {skipped} skipped, {not_found} not found."))
