"""Load mouse gene annotations from a directory of TSV files."""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import Dataset, Gene


class Command(BaseCommand):
    """Load mouse gene symbols and descriptions into Gene records."""

    help = "Load mouse gene annotations from *_go.tsv files."

    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            "directory",
            type=Path,
            help="Directory containing *_go.tsv annotation files.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and report changes without modifying the database.",
        )

    def handle(self, *args, **options):
        """Load annotations from all TSV files."""
        directory = options["directory"]
        dry_run = options["dry_run"]

        if not directory.is_dir():
            raise CommandError(f"Not a directory: {directory}")

        files = sorted(directory.glob("*_go.tsv"))

        if not files:
            raise CommandError(f"No *_go.tsv files found in {directory}")

        self.stdout.write(f"Found {len(files)} annotation files.")

        total_updated = 0
        total_missing = 0

        for path in files:
            dataset_id = path.name.split("_", 1)[0]

            try:
                dataset = Dataset.objects.select_related("species").get(
                    internal_id=dataset_id
                )
            except Dataset.DoesNotExist:
                raise CommandError(
                    f"{path.name}: no Dataset with "
                    f"internal_id='{dataset_id}'"
                )

            self.stdout.write(
                f"\n{path.name} "
                f"→ {dataset.species.scientific_name}"
            )

            annotations = self._read_file(path)

            updated, missing = self._update_genes(
                annotations=annotations,
                species=dataset.species,
                dry_run=dry_run,
            )

            total_updated += updated
            total_missing += missing

            self.stdout.write(f"  annotations: {len(annotations):,}")
            self.stdout.write(f"  matched:     {updated:,}")
            self.stdout.write(f"  missing:     {missing:,}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished. Updated {total_updated:,} genes; "
                f"{total_missing:,} genes were not found."
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run: no database changes made.")
            )

    def _read_file(self, path):
        """Read annotations from one TSV file."""
        annotations = {}

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")

            required_columns = {
                "gene_name",
                "mouse_gene_symbol",
                "mouse_gene_description",
            }

            missing_columns = required_columns - set(reader.fieldnames or [])

            if missing_columns:
                raise CommandError(
                    f"{path.name} is missing columns: "
                    f"{', '.join(sorted(missing_columns))}"
                )

            for line_number, row in enumerate(reader, start=2):
                gene_name = self._clean(row.get("gene_name"))
                symbol = self._clean(row.get("mouse_gene_symbol"))
                description = self._clean(
                    row.get("mouse_gene_description")
                )

                if not gene_name:
                    continue

                if symbol and symbol.upper() == "NA":
                    symbol = None

                if description and description.upper() == "NA":
                    description = None

                if gene_name not in annotations:
                    annotations[gene_name] = {
                        "symbol": symbol,
                        "description": description,
                    }
                    continue

                # Same gene can occur multiple times. Prefer non-empty
                # annotations.
                previous = annotations[gene_name]

                if not previous["symbol"] and symbol:
                    previous["symbol"] = symbol

                if not previous["description"] and description:
                    previous["description"] = description

                if (
                    previous["symbol"]
                    and symbol
                    and previous["symbol"] != symbol
                ):
                    self.stdout.write(
                        self.style.WARNING(
                            f"{path.name}:{line_number}: conflicting "
                            f"symbols for {gene_name}: "
                            f"{previous['symbol']} vs {symbol}"
                        )
                    )

                if (
                    previous["description"]
                    and description
                    and previous["description"] != description
                ):
                    self.stdout.write(
                        self.style.WARNING(
                            f"{path.name}:{line_number}: conflicting "
                            f"descriptions for {gene_name}"
                        )
                    )

        return annotations

    def _update_genes(self, annotations, species, dry_run=False):
        """Update genes belonging to the dataset's species."""
        gene_names = list(annotations)

        genes = Gene.objects.filter(
            species=species,
            name__in=gene_names,
        )

        genes_by_name = {gene.name: gene for gene in genes}

        missing = set(gene_names) - set(genes_by_name)

        updated = []

        for gene_name, annotation in annotations.items():
            gene = genes_by_name.get(gene_name)

            if gene is None:
                continue

            if annotation["symbol"]:
                gene.symbol = annotation["symbol"]

            if annotation["description"]:
                gene.description = annotation["description"]

            updated.append(gene)

        if not dry_run and updated:
            with transaction.atomic():
                Gene.objects.bulk_update(
                    updated,
                    ["symbol", "description"],
                    batch_size=1000,
                )

        return len(updated), len(missing)

    @staticmethod
    def _clean(value):
        """Strip whitespace and normalize empty values."""
        if value is None:
            return None

        value = value.strip()

        return value or None
