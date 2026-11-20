from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import Dataset, ExpressionConservation, Gene, Ortholog


class Command(BaseCommand):
    """Load PESCI expression conservation scores."""

    help = "Load expression conservation scores from PESCI result directories."

    def add_arguments(self, parser):
        parser.add_argument(
            "directory",
            type=Path,
            help="Parent directory containing PESCI result directories.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and show statistics without modifying the database.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Bulk insert batch size.",
        )

    def handle(self, *args, **options):
        directory = options["directory"].resolve()
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if not directory.is_dir():
            raise CommandError(f"Directory does not exist: {directory}")

        # Each immediate subdirectory is one PESCI run.
        pesci_dirs = sorted(
            path for path in directory.iterdir()
            if path.is_dir()
        )

        if not pesci_dirs:
            raise CommandError(
                f"No PESCI directories found in {directory}."
            )

        self.stdout.write(
            f"Found {len(pesci_dirs):,} PESCI directories."
        )
        self.stdout.write("")

        total_stats = {
            "directories": 0,
            "successful": 0,
            "failed": 0,
            "rows": 0,
            "valid_rows": 0,
            "created": 0,
            "skipped": 0,
            "missing_gene1": 0,
            "missing_gene2": 0,
            "missing_ortholog1": 0,
            "missing_ortholog2": 0,
            "mismatched_orthogroup": 0,
        }

        for pesci_dir in pesci_dirs:
            total_stats["directories"] += 1

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"=== {pesci_dir.name} ==="
                )
            )

            try:
                stats = self.process_directory(
                    pesci_dir,
                    dry_run=dry_run,
                    batch_size=batch_size,
                )

            except CommandError as exc:
                total_stats["failed"] += 1

                self.stdout.write(
                    self.style.ERROR(f"FAILED: {exc}")
                )
                self.stdout.write("")
                continue

            total_stats["successful"] += 1

            for key in (
                "rows",
                "valid_rows",
                "created",
                "skipped",
                "missing_gene1",
                "missing_gene2",
                "missing_ortholog1",
                "missing_ortholog2",
                "mismatched_orthogroup",
            ):
                total_stats[key] += stats[key]

            self.stdout.write("")

        # --------------------------------------------------------------
        # Final summary.
        # --------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("=== SUMMARY ===")
        )

        self.stdout.write(
            f"Directories: {total_stats['directories']:,}"
        )
        self.stdout.write(
            f"Successful:  {total_stats['successful']:,}"
        )
        self.stdout.write(
            f"Failed:      {total_stats['failed']:,}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"PESCI rows:  {total_stats['rows']:,}"
        )
        self.stdout.write(
            f"Valid rows:  {total_stats['valid_rows']:,}"
        )

        self.stdout.write("")
        self.stdout.write("Missing genes:")
        self.stdout.write(
            f"  Species 1: {total_stats['missing_gene1']:,}"
        )
        self.stdout.write(
            f"  Species 2: {total_stats['missing_gene2']:,}"
        )

        self.stdout.write("")
        self.stdout.write("Ortholog warnings:")
        self.stdout.write(
            f"  Missing species 1 ortholog: "
            f"{total_stats['missing_ortholog1']:,}"
        )
        self.stdout.write(
            f"  Missing species 2 ortholog: "
            f"{total_stats['missing_ortholog2']:,}"
        )
        self.stdout.write(
            f"  Mismatched orthogroup: "
            f"{total_stats['mismatched_orthogroup']:,}"
        )

        if not dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created: {total_stats['created']:,}"
                )
            )
            self.stdout.write(
                f"Skipped existing: {total_stats['skipped']:,}"
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: database was not modified."
                )
            )

        if total_stats["failed"]:
            raise CommandError(
                f"{total_stats['failed']} PESCI directories failed."
            )

    def process_directory(
        self,
        directory,
        dry_run,
        batch_size,
    ):
        """Process one PESCI directory."""

        # --------------------------------------------------------------
        # Parse dataset IDs from directory name.
        #
        # Example:
        #
        #     acrmil01-stypis01
        #
        # becomes:
        #
        #     acrmil01
        #     stypis01
        # --------------------------------------------------------------
        try:
            dataset1_id, dataset2_id = directory.name.split(
                "-",
                maxsplit=1,
            )
        except ValueError as exc:
            raise CommandError(
                f"Invalid directory name '{directory.name}'. "
                "Expected '<dataset1_internal_id>-<dataset2_internal_id>'."
            ) from exc

        dataset1 = self.get_dataset(dataset1_id)
        dataset2 = self.get_dataset(dataset2_id)

        self.stdout.write(
            f"Datasets: {dataset1.internal_id} -> "
            f"{dataset2.internal_id}"
        )
        self.stdout.write(
            f"Species: {dataset1.species} -> {dataset2.species}"
        )

        # --------------------------------------------------------------
        # Locate expression conservation score file.
        # --------------------------------------------------------------
        score_file = (
            directory
            / f"{dataset1_id}-{dataset2_id}_"
            "expression_conservation_scores.tsv"
        )

        if not score_file.is_file():
            raise CommandError(
                f"Expression conservation file not found: {score_file}"
            )

        # --------------------------------------------------------------
        # Parse the TSV.
        # --------------------------------------------------------------
        parsed_rows = self.parse_file(score_file)

        stats = {
            "rows": len(parsed_rows),
            "valid_rows": 0,
            "created": 0,
            "skipped": 0,
            "missing_gene1": 0,
            "missing_gene2": 0,
            "missing_ortholog1": 0,
            "missing_ortholog2": 0,
            "mismatched_orthogroup": 0,
        }

        self.stdout.write(
            f"Rows: {len(parsed_rows):,}"
        )

        # --------------------------------------------------------------
        # Collect all unique gene names first.
        #
        # This allows us to do one query per species rather than one
        # query per PESCI row.
        # --------------------------------------------------------------
        gene_names1 = {
            row["gene1_name"]
            for row in parsed_rows
        }

        gene_names2 = {
            row["gene2_name"]
            for row in parsed_rows
        }

        # --------------------------------------------------------------
        # Load all genes for species 1.
        # --------------------------------------------------------------
        genes1 = {
            gene.name: gene
            for gene in Gene.objects.filter(
                species=dataset1.species,
                name__in=gene_names1,
            )
        }

        # --------------------------------------------------------------
        # Load all genes for species 2.
        # --------------------------------------------------------------
        genes2 = {
            gene.name: gene
            for gene in Gene.objects.filter(
                species=dataset2.species,
                name__in=gene_names2,
            )
        }

        missing_genes1 = gene_names1 - genes1.keys()
        missing_genes2 = gene_names2 - genes2.keys()

        stats["missing_gene1"] = len(missing_genes1)
        stats["missing_gene2"] = len(missing_genes2)

        self.stdout.write(
            f"Genes 1: {len(genes1):,}/{len(gene_names1):,} found"
        )
        self.stdout.write(
            f"Genes 2: {len(genes2):,}/{len(gene_names2):,} found"
        )

        if missing_genes1:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {len(missing_genes1):,} "
                    "genes not found for species 1."
                )
            )

        if missing_genes2:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {len(missing_genes2):,} "
                    "genes not found for species 2."
                )
            )

        # --------------------------------------------------------------
        # Load all orthologs for the genes we found.
        #
        # Again, this is done with one query per species.
        # --------------------------------------------------------------
        gene_ids1 = [gene.pk for gene in genes1.values()]
        gene_ids2 = [gene.pk for gene in genes2.values()]

        orthologs1 = {
            ortholog.gene_id: ortholog
            for ortholog in Ortholog.objects.filter(
                species=dataset1.species,
                gene_id__in=gene_ids1,
            ).select_related("orthogroup")
        }

        orthologs2 = {
            ortholog.gene_id: ortholog
            for ortholog in Ortholog.objects.filter(
                species=dataset2.species,
                gene_id__in=gene_ids2,
            ).select_related("orthogroup")
        }

        # --------------------------------------------------------------
        # Build ExpressionConservation objects in memory.
        #
        # Missing orthologs and mismatched orthogroups are warnings,
        # NOT fatal errors.
        #
        # A row is imported whenever both genes exist and at least one
        # ortholog provides an orthogroup.
        # --------------------------------------------------------------
        rows = []

        for parsed in parsed_rows:
            gene1 = genes1.get(parsed["gene1_name"])
            gene2 = genes2.get(parsed["gene2_name"])

            # These rows cannot be represented without both genes.
            if gene1 is None or gene2 is None:
                continue

            ortholog1 = orthologs1.get(gene1.pk)
            ortholog2 = orthologs2.get(gene2.pk)

            orthogroup = None

            if ortholog1 is None:
                stats["missing_ortholog1"] += 1

            if ortholog2 is None:
                stats["missing_ortholog2"] += 1

            if ortholog1 is not None and ortholog2 is not None:
                if ortholog1.orthogroup_id != ortholog2.orthogroup_id:
                    stats["mismatched_orthogroup"] += 1
                else:
                    orthogroup = ortholog1.orthogroup

            # If only one ortholog exists, use its orthogroup.
            if orthogroup is None:
                if ortholog1 is not None:
                    orthogroup = ortholog1.orthogroup
                elif ortholog2 is not None:
                    orthogroup = ortholog2.orthogroup

            # ExpressionConservation.orthogroup is required, so a row
            # with no ortholog on either side cannot be inserted.
            if orthogroup is None:
                continue

            rows.append(
                ExpressionConservation(
                    orthogroup=orthogroup,
                    gene=gene1,
                    gene2=gene2,
                    dataset=dataset1,
                    dataset2=dataset2,
                    conservation_score=parsed["score"],
                    is_one_to_one=parsed["is_one_to_one"],
                )
            )

        stats["valid_rows"] = len(rows)

        self.stdout.write(
            f"Valid rows: {len(rows):,}"
        )

        # --------------------------------------------------------------
        # Warnings.
        # --------------------------------------------------------------
        if stats["missing_ortholog1"]:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {stats['missing_ortholog1']:,} rows "
                    "have no ortholog for species 1."
                )
            )

        if stats["missing_ortholog2"]:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {stats['missing_ortholog2']:,} rows "
                    "have no ortholog for species 2."
                )
            )

        if stats["mismatched_orthogroup"]:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {stats['mismatched_orthogroup']:,} rows "
                    "have different orthogroups for the two genes."
                )
            )

        # --------------------------------------------------------------
        # Dry run stops here.
        # --------------------------------------------------------------
        if dry_run:
            return stats

        # --------------------------------------------------------------
        # Insert only rows that don't already exist.
        # --------------------------------------------------------------
        created, skipped = self.save_rows(
            rows,
            dataset1,
            dataset2,
            batch_size,
        )

        stats["created"] = created
        stats["skipped"] = skipped

        self.stdout.write(
            f"Created: {created:,}; "
            f"skipped existing: {skipped:,}"
        )

        return stats

    @staticmethod
    def get_dataset(internal_id):
        """Get a dataset by internal ID."""

        try:
            return Dataset.objects.select_related(
                "species"
            ).get(
                internal_id=internal_id
            )
        except Dataset.DoesNotExist as exc:
            raise CommandError(
                f"Dataset '{internal_id}' does not exist."
            ) from exc

    @staticmethod
    def parse_file(score_file):
        """Parse PESCI expression conservation TSV."""

        expected_header = [
            "genes sp1",
            "genes sp2",
            "expression conservation",
            "is_one2one",
        ]

        rows = []

        with score_file.open("r", encoding="utf-8") as handle:
            header = handle.readline().rstrip("\r\n").split("\t")

            if header != expected_header:
                raise CommandError(
                    f"Unexpected header in {score_file}.\n"
                    f"Expected: {expected_header}\n"
                    f"Found: {header}"
                )

            for line_number, line in enumerate(handle, start=2):
                line = line.rstrip("\r\n")

                if not line:
                    continue

                fields = line.split("\t")

                if len(fields) != 4:
                    raise CommandError(
                        f"{score_file}:{line_number}: "
                        f"expected 4 columns, found {len(fields)}."
                    )

                gene1_name, gene2_name, score, is_one2one = fields

                try:
                    score = float(score)
                except ValueError as exc:
                    raise CommandError(
                        f"{score_file}:{line_number}: "
                        f"invalid score '{score}'."
                    ) from exc

                try:
                    is_one_to_one = bool(float(is_one2one))
                except ValueError as exc:
                    raise CommandError(
                        f"{score_file}:{line_number}: "
                        f"invalid is_one2one '{is_one2one}'."
                    ) from exc

                rows.append(
                    {
                        "gene1_name": gene1_name,
                        "gene2_name": gene2_name,
                        "score": score,
                        "is_one_to_one": is_one_to_one,
                    }
                )

        return rows

    @staticmethod
    @transaction.atomic
    def save_rows(rows, dataset1, dataset2, batch_size):
        """Insert new expression conservation records only."""

        if not rows:
            return 0, 0

        # --------------------------------------------------------------
        # Find existing records for this dataset pair.
        #
        # We only query relevant genes to avoid loading unrelated
        # expression conservation records.
        # --------------------------------------------------------------
        gene_ids1 = {
            row.gene_id
            for row in rows
        }

        gene_ids2 = {
            row.gene2_id
            for row in rows
        }

        existing_keys = set(
            ExpressionConservation.objects.filter(
                dataset=dataset1,
                dataset2=dataset2,
                gene_id__in=gene_ids1,
                gene2_id__in=gene_ids2,
            ).values_list(
                "gene_id",
                "gene2_id",
                "dataset_id",
                "dataset2_id",
            )
        )

        to_create = []

        for row in rows:
            key = (
                row.gene_id,
                row.gene2_id,
                row.dataset_id,
                row.dataset2_id,
            )

            if key not in existing_keys:
                to_create.append(row)

        # --------------------------------------------------------------
        # Insert in batches.
        # --------------------------------------------------------------
        if to_create:
            ExpressionConservation.objects.bulk_create(
                to_create,
                batch_size=batch_size,
            )

        skipped = len(rows) - len(to_create)

        return len(to_create), skipped
