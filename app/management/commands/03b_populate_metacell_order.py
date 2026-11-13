"""Import metacell ordering from flattened tree TSV files."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import Dataset, Metacell


class Command(BaseCommand):
    """Import metacell order positions from TSV files."""

    help = "Import metacell order positions from *.flattened_tree_metacell_order.tsv files."

    FILE_SUFFIX = ".flattened_tree_metacell_order.tsv"

    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            "directory",
            type=Path,
            help="Directory containing flattened_tree_metacell_order.tsv files.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate files without modifying the database.",
        )

    def handle(self, *args, **options):
        """Run the import."""
        directory = options["directory"]
        dry_run = options["dry_run"]

        if not directory.is_dir():
            raise CommandError(f"Directory does not exist: {directory}")

        files = sorted(directory.glob(f"*{self.FILE_SUFFIX}"))

        if not files:
            self.stdout.write(
                self.style.WARNING(
                    f"No *{self.FILE_SUFFIX} files found in {directory}"
                )
            )
            return

        total_updated = 0
        total_missing = 0

        for filepath in files:
            updated, missing = self.import_file(filepath, dry_run=dry_run)
            total_updated += updated
            total_missing += missing

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated: {total_updated}, missing: {total_missing}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run: no database changes were made.")
            )

    def import_file(self, filepath, dry_run=False):
        """Import a single metacell order file."""
        dataset_internal_id = filepath.name.removesuffix(self.FILE_SUFFIX)

        self.stdout.write(f"\nProcessing {filepath.name}")
        self.stdout.write(f"  Dataset: {dataset_internal_id}")

        try:
            dataset = Dataset.objects.get(internal_id=dataset_internal_id)
        except Dataset.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"  Dataset with internal_id={dataset_internal_id!r} "
                    "does not exist."
                )
            )
            return 0, 0

        orders = {}
        invalid_rows = 0

        with filepath.open("r", encoding="utf-8") as file:
            header = file.readline().strip().split("\t")

            expected_header = ["metacell", "order_position", "color"]
            if header != expected_header:
                raise CommandError(
                    f"{filepath}: expected header "
                    f"{expected_header}, got {header}"
                )

            for line_number, line in enumerate(file, start=2):
                line = line.strip()

                if not line:
                    continue

                fields = line.split("\t")

                if len(fields) != 3:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Line {line_number}: expected 3 columns, "
                            f"got {len(fields)}"
                        )
                    )
                    invalid_rows += 1
                    continue

                metacell_name, order_position, _color = fields

                try:
                    order_position = int(order_position)
                except ValueError:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Line {line_number}: invalid order position "
                            f"{order_position!r}"
                        )
                    )
                    invalid_rows += 1
                    continue

                orders[metacell_name] = order_position

        metacells = {
            metacell.name: metacell
            for metacell in Metacell.objects.filter(
                dataset=dataset,
                name__in=orders,
            )
        }

        missing = set(orders) - set(metacells)

        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"  Missing {len(missing)} metacells:"
                )
            )
            for name in sorted(missing):
                self.stdout.write(f"    {name}")

        to_update = []

        for name, order_position in orders.items():
            metacell = metacells.get(name)

            if metacell is None:
                continue

            if metacell.order != order_position:
                metacell.order = order_position
                to_update.append(metacell)

        self.stdout.write(
            f"  Rows: {len(orders)}"
        )
        self.stdout.write(
            f"  Changes: {len(to_update)}"
        )
        self.stdout.write(
            f"  Missing metacells: {len(missing)}"
        )
        self.stdout.write(
            f"  Invalid rows: {invalid_rows}"
        )

        if not dry_run and to_update:
            with transaction.atomic():
                Metacell.objects.bulk_update(
                    to_update,
                    ["order"],
                    batch_size=1000,
                )

        return len(to_update), len(missing)
