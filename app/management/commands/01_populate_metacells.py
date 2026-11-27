"""Load metacell and single-cell data."""

from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import CellType, Dataset, Metacell, MetacellType, SingleCell

DEFAULT_COLOR = "#AAAAAA"
CELL_SUFFIX = ".cell_umap_coordinates.tsv"
METACELL_SUFFIX = ".metacell_projected_on_cell_umap_coordinates.tsv"
TYPE_COLOR_SUFFIX = "_cell_to_celltype_broad_colored.tsv"
TYPE_SUFFIX = ".cell_to_celltype.tsv"


class Command(BaseCommand):
    """Populate cell and metacell tables from TSV files."""

    help = "Load CellType, Dataset, MetacellType, Metacell and SingleCell data."

    def add_arguments(self, parser):
        parser.add_argument("data_directory", type=Path, help="Directory containing the input TSV files.")
        parser.add_argument("datasets", nargs="*", help="Dataset prefixes to load. If omitted, load all datasets.")
        parser.add_argument("--replace", action="store_true", help="Datasets to load. If omitted, load all datasets.")

    def handle(self, *args, **options):
        data_dir = options["data_directory"]
        replace = options["replace"]
        requested = set(options["datasets"])

        if not data_dir.is_dir():
            raise CommandError(f"Data directory does not exist: {data_dir}")

        cell_files = sorted(data_dir.glob(f"*{CELL_SUFFIX}"))
        if requested:
            cell_files = [path for path in cell_files if path.name.removesuffix(CELL_SUFFIX) in requested]

        if not cell_files:
            raise CommandError("No matching dataset files found.")

        loaded = skipped = 0

        for cell_file in cell_files:
            dataset_id = cell_file.name.removesuffix(CELL_SUFFIX)
            metacell_file = data_dir / f"{dataset_id}{METACELL_SUFFIX}"
            type_color_file = data_dir / f"{dataset_id}{TYPE_COLOR_SUFFIX}"

            if not metacell_file.exists():
                self.stdout.write(self.style.ERROR(f"{dataset_id}: missing {metacell_file.name}; skipping."))
                skipped += 1
                continue

            if not type_color_file.exists():
                type_color_file = data_dir / f"{dataset_id}{TYPE_SUFFIX}"

            if not type_color_file.exists():
                self.stdout.write(self.style.ERROR(f"{dataset_id}: missing {type_color_file.name}; skipping."))
                skipped += 1
                continue

            dataset = Dataset.objects.filter(internal_id=dataset_id).first()
            if dataset is None:
                self.stdout.write(self.style.ERROR(f"{dataset_id}: Dataset not found; skipping."))
                skipped += 1
                continue

            # Check if models are already loaded
            models = (SingleCell, Metacell, CellType, MetacellType)
            if any(model.objects.filter(dataset=dataset).exists() for model in models):
                if not replace:
                    self.stdout.write(self.style.WARNING(f"{dataset_id}: already loaded; skipping."))
                    skipped += 1
                    continue
                else:
                    self.stdout.write(self.style.WARNING(f"{dataset_id}: already loaded; replacing its contents."))

            self.stdout.write(f"\nProcessing {dataset_id}...")
            stats = self.load_dataset(dataset, cell_file, metacell_file, type_color_file, replace=replace)
            loaded += 1

            self.stdout.write(self.style.SUCCESS(
                f"CellTypes={stats['cell_types']}, "
                f"MetacellTypes={stats['metacell_types']}, "
                f"Metacells={stats['metacells']}, "
                f"SingleCells={stats['single_cells']}"
            ))

        self.stdout.write(self.style.SUCCESS(f"\nDone. Loaded {loaded} dataset(s); skipped {skipped}."))

    def load_dataset(self, dataset, cell_file, metacell_file, type_color_file, replace=False):
        cell_df = self.read_file(
            cell_file,
            {"cell", "UMAP_1", "UMAP_2", "metacell", "cell_type"},
            {"cell": "string", "metacell": "string", "cell_type": "string"},
        )
        metacell_df = self.read_file(metacell_file, {"metacell", "UMAP_1", "UMAP_2"}, {"metacell": "string"})
        self.validate_files(cell_df, metacell_df)

        try:
            color_df = self.read_file(
                type_color_file,
                {"cell", "cell_type_broad", "color"},
                {"cell": "string", "cell_type_broad": "string", "color": "string"},
            )
        except CommandError:
            # Try reading file without expecting color
            color_df = self.read_file(type_color_file, {"cell", "cell_type"}, {"cell": "string", "cell_type": "string"})
            color_df["cell_type_broad"] = color_df["cell_type"]
            color_df["color"] = DEFAULT_COLOR

        with transaction.atomic():
            if replace:
                SingleCell.objects.filter(dataset=dataset).delete()
                Metacell.objects.filter(dataset=dataset).delete()
                CellType.objects.filter(dataset=dataset).delete()
                MetacellType.objects.filter(dataset=dataset).delete()

            cell_types = self.load_types(CellType, dataset, cell_df, color_df)
            metacell_df = self.assign_metacell_types(cell_df, metacell_df)
            metacell_types = self.load_types(MetacellType, dataset, metacell_df, color_df)
            metacells = self.load_metacells(dataset, metacell_df, metacell_types)
            single_cells = self.load_single_cells(dataset, cell_df, metacells, cell_types)

        return {
            "cell_types": len(cell_types),
            "metacell_types": len(metacell_types),
            "metacells": len(metacells),
            "single_cells": single_cells,
        }

    @staticmethod
    def read_file(path, required, dtypes):
        df = pd.read_csv(path, sep="\t", dtype=dtypes, keep_default_na=True, na_values=["nan", "NaN", "NA", ""])

        missing = required - set(df.columns)
        if missing:
            raise CommandError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")

        for column in ("UMAP_1", "UMAP_2"):
            if column in df:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        return df

    @staticmethod
    def validate_files(cell_df, metacell_df):
        cell_metacells = set(cell_df.loc[cell_df["metacell"].notna(), "metacell"])
        projected_metacells = set(metacell_df.loc[metacell_df["metacell"].notna(), "metacell"])
        missing = cell_metacells - projected_metacells
        if missing:
            examples = ", ".join(sorted(missing)[:10])
            raise CommandError(
                f"{len(missing)} metacells referenced by the cell file are missing from the metacell file. "
                f"Examples: {examples}"
            )


    @staticmethod
    def assign_metacell_types(cell_df, metacell_df):
        """Return the most frequent cell type for each metacell."""
        types = (
            cell_df
            .dropna(subset=["metacell", "cell_type"])
            .groupby(["metacell", "cell_type"])
            .size()
            .reset_index(name="count")
            .sort_values(["metacell", "count"], ascending=[True, False])
            .drop_duplicates("metacell")
        )

        return metacell_df.merge(types, on="metacell", how="left")


    @staticmethod
    def load_types(model, dataset, df, color_df):
        names = { str(value).strip() for value in df["cell_type"].dropna() if str(value).strip() }
        if not names:
            return {}

        colors = dict(zip(color_df["cell_type_broad"].str.strip(), color_df["color"].str.strip()))
        model.objects.bulk_create(
            [model(dataset=dataset, name=name, color=colors.get(name, DEFAULT_COLOR)) for name in names],
            batch_size=5000,
            ignore_conflicts=True,
        )
        return dict(model.objects.filter(dataset=dataset, name__in=names).values_list("name", "id"))

    @staticmethod
    def load_metacells(dataset, metacell_df, metacell_types):
        rows = metacell_df.drop_duplicates("metacell", keep="last")
        if rows.empty:
            return {}

        names = set(rows["metacell"].astype(str).str.strip())
        data = [
            Metacell(
                dataset=dataset,
                name=str(row.metacell).strip(),
                type_id=metacell_types.get(str(row.cell_type).strip()),
                x=None if pd.isna(row.UMAP_1) else float(row.UMAP_1),
                y=None if pd.isna(row.UMAP_2) else float(row.UMAP_2),
            )
            for row in rows.itertuples(index=False)
        ]
        Metacell.objects.bulk_create(data, batch_size=5000, ignore_conflicts=True)
        return dict(Metacell.objects.filter(dataset=dataset, name__in=names).values_list("name", "id"))

    @staticmethod
    def load_single_cells(dataset, cell_df, metacells, cell_types):
        rows = cell_df[cell_df["cell"].notna()].drop_duplicates("cell", keep="last")
        if rows.empty:
            return 0

        data = [
            SingleCell(
                dataset=dataset,
                name=str(row.cell).strip(),
                metacell_id=metacells.get(str(row.metacell).strip()) if pd.notna(row.metacell) else None,
                type_id=cell_types.get(str(row.cell_type).strip()) if pd.notna(row.cell_type) else None,
                x=None if pd.isna(row.UMAP_1) else float(row.UMAP_1),
                y=None if pd.isna(row.UMAP_2) else float(row.UMAP_2),
            )
            for row in rows.itertuples(index=False)
        ]
        SingleCell.objects.bulk_create(data, batch_size=10000, ignore_conflicts=True)

        return len(rows)
