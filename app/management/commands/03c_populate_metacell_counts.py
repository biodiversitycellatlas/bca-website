import time

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from app.models import (
    Dataset,
    Metacell,
    MetacellCount,
    MetacellGeneExpression,
    SingleCell,
)


class Command(BaseCommand):
    """Populate MetacellCount efficiently from source data."""

    help = "Populate MetacellCount statistics for all datasets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            type=int,
            help="Only process a specific dataset ID.",
        )

    def handle(self, *args, **options):
        dataset_id = options.get("dataset")

        datasets = Dataset.objects.order_by("id")

        if dataset_id:
            datasets = datasets.filter(id=dataset_id)

        total_datasets = datasets.count()

        if not total_datasets:
            self.stdout.write(self.style.WARNING("No datasets found."))
            return

        total_counts = 0
        overall_start = time.monotonic()

        self.stdout.write(
            f"Found {total_datasets:,} dataset(s) to process."
        )

        for dataset_number, dataset in enumerate(
            datasets.iterator(),
            start=1,
        ):
            dataset_start = time.monotonic()

            self.stdout.write(
                f"\n{'=' * 70}"
            )
            self.stdout.write(
                f"[{dataset_number}/{total_datasets}] "
                f"Processing: {dataset}"
            )
            self.stdout.write(
                f"Dataset ID: {dataset.id}"
            )

            # -------------------------------------------------------------
            # Get metacells
            # -------------------------------------------------------------
            self.stdout.write("  → Loading metacells...", ending="")
            self.stdout.flush()

            start = time.monotonic()

            metacell_ids = list(
                Metacell.objects
                .filter(dataset_id=dataset.id)
                .values_list("id", flat=True)
            )

            elapsed = time.monotonic() - start

            self.stdout.write(
                self.style.SUCCESS(
                    f" done ({len(metacell_ids):,} metacells, "
                    f"{elapsed:.2f}s)"
                )
            )

            if not metacell_ids:
                self.stdout.write(
                    self.style.WARNING("  → No metacells found, skipping.")
                )
                continue

            # -------------------------------------------------------------
            # Count single cells
            # -------------------------------------------------------------
            self.stdout.write(
                "  → Counting single cells per metacell...",
                ending="",
            )
            self.stdout.flush()

            start = time.monotonic()

            cell_counts = dict(
                SingleCell.objects
                .filter(
                    dataset_id=dataset.id,
                    metacell_id__in=metacell_ids,
                )
                .values("metacell_id")
                .annotate(cells=Count("id"))
                .values_list("metacell_id", "cells")
            )

            elapsed = time.monotonic() - start
            total_cells = sum(cell_counts.values())

            self.stdout.write(
                self.style.SUCCESS(
                    f" done ({total_cells:,} cells, {elapsed:.2f}s)"
                )
            )

            # -------------------------------------------------------------
            # Calculate UMI totals
            # -------------------------------------------------------------
            self.stdout.write(
                "  → Calculating UMI totals per metacell...",
                ending="",
            )
            self.stdout.flush()

            start = time.monotonic()

            umi_counts = dict(
                MetacellGeneExpression.objects
                .filter(
                    dataset_id=dataset.id,
                    metacell_id__in=metacell_ids,
                )
                .values("metacell_id")
                .annotate(umis=Sum("umi_raw"))
                .values_list("metacell_id", "umis")
            )

            elapsed = time.monotonic() - start

            total_umis = sum(
                value or 0
                for value in umi_counts.values()
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f" done ({len(umi_counts):,} metacells with "
                    f"expression, {elapsed:.2f}s)"
                )
            )

            # -------------------------------------------------------------
            # Delete existing records
            # -------------------------------------------------------------
            self.stdout.write(
                "  → Removing existing MetacellCount records...",
                ending="",
            )
            self.stdout.flush()

            start = time.monotonic()

            deleted, _ = MetacellCount.objects.filter(
                dataset_id=dataset.id
            ).delete()

            elapsed = time.monotonic() - start

            self.stdout.write(
                self.style.SUCCESS(
                    f" done ({deleted:,} deleted, {elapsed:.2f}s)"
                )
            )

            # -------------------------------------------------------------
            # Create new records
            # -------------------------------------------------------------
            self.stdout.write(
                f"  → Creating {len(metacell_ids):,} MetacellCount records...",
                ending="",
            )
            self.stdout.flush()

            start = time.monotonic()

            counts = [
                MetacellCount(
                    dataset_id=dataset.id,
                    metacell_id=metacell_id,
                    cells=cell_counts.get(metacell_id, 0),
                    umis=umi_counts.get(metacell_id) or 0,
                )
                for metacell_id in metacell_ids
            ]

            MetacellCount.objects.bulk_create(
                counts,
                batch_size=5000,
            )

            elapsed = time.monotonic() - start

            self.stdout.write(
                self.style.SUCCESS(
                    f" done ({len(counts):,} records, {elapsed:.2f}s)"
                )
            )

            # -------------------------------------------------------------
            # Dataset summary
            # -------------------------------------------------------------
            dataset_elapsed = time.monotonic() - dataset_start
            total_counts += len(counts)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Dataset complete in {dataset_elapsed:.2f}s"
                )
            )

        # -----------------------------------------------------------------
        # Final summary
        # -----------------------------------------------------------------
        elapsed = time.monotonic() - overall_start

        self.stdout.write(
            f"\n{'=' * 70}"
        )
        self.stdout.write(
            self.style.SUCCESS(
                "DONE"
            )
        )
        self.stdout.write(
            f"  Datasets processed: {total_datasets:,}"
        )
        self.stdout.write(
            f"  MetacellCount records: {total_counts:,}"
        )
        self.stdout.write(
            f"  Total time: {elapsed:.2f}s"
        )
