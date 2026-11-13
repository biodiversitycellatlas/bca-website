import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import connection

from app.models import Dataset, Gene, GeneCorrelation


TOP_N = 100
ROW_CHUNK_SIZE = 512
COPY_CHUNK_SIZE = 20_000
FILE_SUFFIX = ".gene_correlations.pkl"

class Command(BaseCommand):
    help = "Load top positive and negative gene correlations from pickle files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=Path,
            required=True,
            help="Directory to recursively search for gene correlation pickle files.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Process files without modifying the database.")

    def handle(self, *args, **options):
        directory = options["dir"].resolve()
        dry_run = options["dry_run"]

        if not directory.is_dir():
            self.stdout.write(self.style.ERROR(f"Directory does not exist: {directory}"))
            return

        files = sorted(directory.rglob(f"*{FILE_SUFFIX}"))

        if not files:
            self.stdout.write(self.style.WARNING(f"No correlation files found in {directory}"))
            return

        self.stdout.write(f"Found {len(files)} correlation files.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: database will not be modified."))

        for path in files:
            self.load_file(path, dry_run=dry_run)

    def load_file(self, path, dry_run=False):
        filename = path.name
        internal_id = filename[: -len(FILE_SUFFIX)]

        try:
            dataset = Dataset.objects.select_related("species").get(internal_id=internal_id)
        except Dataset.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"{filename}: no Dataset found with internal_id={internal_id!r}"))
            return
        except Dataset.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR(f"{filename}: multiple Datasets found with internal_id={internal_id!r}"))
            return

        species = dataset.species
        # Skip species that already has correlations.
        if GeneCorrelation.objects.filter(dataset__species=species).exists():
            msg <- f"{filename}: correlations already loaded for {species.scientific_name}; skipping."
            self.stdout.write(self.style.WARNING(msg))
            return

        self.stdout.write(f"{filename}: loading correlations for {species.scientific_name}")

        # Load pickle
        with path.open("rb") as fh:
            correlations = pickle.load(fh)

        if not isinstance(correlations, pd.DataFrame):
            msg <- f"{filename}: expected pandas DataFrame, got {type(correlations).__name__}"
            self.stdout.write(self.style.ERROR(msg))
            return

        self.stdout.write(f"{filename}: matrix shape = {correlations.shape}")

        # Remove duplicate rows/columns
        if correlations.index.duplicated().any():
            n_duplicates = correlations.index.duplicated().sum()

            self.stdout.write(f"{filename}: removing {n_duplicates:,} duplicate gene IDs")
            correlations = correlations.loc[~correlations.index.duplicated(keep="first")]

        if correlations.columns.duplicated().any():
            n_duplicates = correlations.columns.duplicated().sum()

            self.stdout.write(f"{filename}: removing {n_duplicates:,} duplicate gene IDs from columns")
            correlations = correlations.loc[:, ~correlations.columns.duplicated(keep="first")]

        # Match matrix genes to database genes
        matrix_gene_names = set(correlations.index) & set(correlations.columns)
        genes = {
            gene.name: gene.id
            for gene in Gene.objects.filter(species=species, name__in=matrix_gene_names).only("id", "name")
        }

        missing = matrix_gene_names - genes.keys()
        if missing:
            msg <- f"{filename}: {len(missing):,} genes from the matrix were not found in the database."
            self.stdout.write(self.style.WARNING(msg))

        gene_names = [name for name in correlations.index if name in genes and name in correlations.columns]
        self.stdout.write(f"{filename}: {len(gene_names):,} genes matched in database")

        if len(gene_names) < 2:
            self.stdout.write(self.style.WARNING(f"{filename}: fewer than 2 matched genes; skipping."))
            return

        # Extract matrix
        matrix = correlations.loc[gene_names, gene_names].to_numpy(dtype=np.float64, copy=False)

        del correlations
        gene_ids = np.asarray([genes[name] for name in gene_names], dtype=np.int64)
        n_genes = len(gene_names)
        self.stdout.write(f"{filename}: processing {n_genes:,} genes in chunks of {ROW_CHUNK_SIZE:,}")

        # Process matrix in chunks
        copy_rows = []
        total_rows = 0

        for start in range(0, n_genes, ROW_CHUNK_SIZE):
            end = min(start + ROW_CHUNK_SIZE, n_genes)

            chunk = matrix[start:end]
            rows = self.get_correlation_rows(chunk=chunk, row_start=start, gene_ids=gene_ids)

            if dry_run:
                total_rows += len(rows)
            else:
                copy_rows.extend(rows)

                # Keep COPY buffers reasonably small.
                while len(copy_rows) >= COPY_CHUNK_SIZE:
                    batch = copy_rows[: COPY_CHUNK_SIZE]

                    del copy_rows[: COPY_CHUNK_SIZE]
                    self.copy_to_database(dataset_id=dataset.id, rows=batch)
                    total_rows += len(batch)

            if end == n_genes or end % 2000 < ROW_CHUNK_SIZE:
                self.stdout.write(f"{filename}: processed {end}/{n_genes:,} genes; {total_rows} correlations loaded")

        # Final COPY batch
        if not dry_run and copy_rows:
            self.copy_to_database(dataset_id=dataset.id, rows=copy_rows)
            total_rows += len(copy_rows)

        if dry_run:
            msg <- f"{filename}: DRY RUN — would load {total_rows:,} correlations"
        else:
            msg <- f"{filename}: loaded {total_rows:,} correlations"
        self.stdout.write(self.style.SUCCESS(msg))

    def get_correlation_rows(self, chunk, row_start, gene_ids):
        """Find top positive and negative correlations for a chunk of rows."""
        n_rows, n_genes = chunk.shape

        # Positive correlations
        positive = np.where(chunk > 0, chunk, -np.inf)
        positive_count = min(TOP_N, max(0, n_genes - 1))

        if positive_count:
            positive_indices = np.argpartition(positive, -positive_count, axis=1)[:, -positive_count:]
        else:
            positive_indices = np.empty((n_rows, 0), dtype=np.intp)

        # Negative correlations
        negative = np.where(chunk < 0, chunk, np.inf)
        negative_count = min(TOP_N, max(0, n_genes - 1))

        if negative_count:
            negative_indices = np.argpartition(negative, negative_count - 1, axis=1)[:, :negative_count]
        else:
            negative_indices = np.empty((n_rows, 0), dtype=np.intp)

        # Build positive output arrays
        row_indices = np.arange(row_start, row_start + n_rows)
        positive_row_indices = np.repeat(row_indices, positive_indices.shape[1])
        positive_col_indices = positive_indices.ravel()
        positive_values = chunk[positive_row_indices - row_start, positive_col_indices]

        # Build negative output arrays
        negative_row_indices = np.repeat(row_indices, negative_indices.shape[1])
        negative_col_indices = negative_indices.ravel()
        negative_values = chunk[negative_row_indices - row_start, negative_col_indices]

        # Combine positive and negative correlations
        row_indices_all = np.concatenate([positive_row_indices, negative_row_indices])
        col_indices_all = np.concatenate([positive_col_indices, negative_col_indices])
        values_all = np.concatenate([positive_values, negative_values])

        # Since correlation is symmetric, only keep one direction of each pair.
        first_ids = gene_ids[row_indices_all]
        second_ids = gene_ids[col_indices_all]

        valid = (first_ids != second_ids) & np.isfinite(values_all) & (first_ids < second_ids)
        first_ids = first_ids[valid]
        second_ids = second_ids[valid]
        values_all = values_all[valid]

        # Remove duplicate gene pairs
        if first_ids.size:
            pairs = np.column_stack((first_ids, second_ids))
            _, unique_indices = np.unique(pairs, axis=0, return_index=True)
            unique_indices.sort()

            first_ids = first_ids[unique_indices]
            second_ids = second_ids[unique_indices]
            values_all = values_all[unique_indices]

        # Convert to Python tuples for PostgreSQL COPY
        return list(zip(first_ids.tolist(), second_ids.tolist(), values_all.tolist()))

    def copy_to_database(self, dataset_id, rows):
        """Insert rows using PostgreSQL COPY."""

        if not rows:
            return

        table = GeneCorrelation._meta.db_table
        q_table = connection.ops.quote_name(table)

        sql = f"COPY {q_table} (dataset_id, gene_id, gene2_id, pearson) FROM STDIN WITH (FORMAT csv)"

        with connection.cursor() as cursor:
            with cursor.copy(sql) as copy:
                for gene_id, gene2_id, pearson in rows:
                    copy.write(f"{dataset_id}, {gene_id}, {gene2_id}, {pearson:.6f}\n")
