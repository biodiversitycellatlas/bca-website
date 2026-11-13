import re
import sys
import unicodedata
from typing import TextIO

from django.core.management.base import BaseCommand
from django.db.models import Count, Prefetch, Q

from app.models import (
    CellType,
    Dataset,
    DatasetFile,
    DatasetQualityControl,
    ExpressionConservation,
    GeneCorrelation,
    GeneModule,
    Metacell,
    MetacellGeneExpression,
    MetacellType,
    MetacellTypeSimilarity,
    Meta,
    SingleCell,
    SpeciesFile,
)

SPECIES_FILE_TYPES = ["Proteome", "DIAMOND", "eggnog-mapper"]
REQUIRED_TAXONOMY_KEYS = ["taxon_id", "kingdom", "phylum"]

# Plain symbols (used when writing to file)
CHECK_PLAIN = "\u2714"
CROSS_PLAIN = "\u2718"

# Colored symbols (used when writing to terminal)
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
CHECK_COLOR = f"{GREEN}{CHECK_PLAIN}{RESET}"
CROSS_COLOR = f"{RED}{CROSS_PLAIN}{RESET}"


class Command(BaseCommand):
    """Show data completeness report for all datasets."""

    help = "Print a data completeness report with missing details and summary table."

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self._use_color = True

    def add_arguments(self, parser):
        parser.add_argument("--species", type=str, default=None, help="Filter by species slug.")
        parser.add_argument("--output", type=str, default=None, help="Write markdown output to a file.")

    def handle(self, *args, **options):
        datasets = (
            Dataset.objects.select_related("species", "publication")
            .prefetch_related(
                Prefetch("species__meta_set", queryset=Meta.objects.all()),
                Prefetch("species__files", queryset=SpeciesFile.objects.all()),
            )
            .order_by("species__scientific_name", "order")
        )

        species_slug = options.get("species")
        if species_slug:
            datasets = datasets.filter(species__slug=species_slug)

        datasets = list(datasets)
        if not datasets:
            self.stdout.write("No datasets found.")
            return

        datasets = self.annotate_counts(datasets)

        # Compute missing once per dataset
        total = len(datasets)
        for i, ds in enumerate(datasets, 1):
            label = ds.internal_id or ds.species.scientific_name
            sys.stderr.write(f"\r{YELLOW}[{i}/{total}] {label}{RESET}")
            sys.stderr.flush()
            ds._missing = self.check_missing(ds)
        sys.stderr.write("\n")

        sections = []
        sections.append(self.render_missing_section(datasets))
        sections.append(self.render_table_section(datasets))

        output = "\n".join(sections)
        out_path = options.get("output")
        if out_path:
            self._use_color = False
            with open(out_path, "w") as f:
                f.write(output + "\n")
            self.stdout.write(self.style.SUCCESS(f"Report written to {out_path}"))
        else:
            self.stdout.write(output)


    def check_missing(self, ds):
        """Return dict of category -> list of missing item descriptions."""
        missing = {}
        species = ds.species

        # Species metadata
        sp_meta_keys = {m.key for m in species.meta_set.all()}
        sp_missing = []
        if not species.image_url:
            sp_missing.append("image")
        missing_taxonomy = [k for k in REQUIRED_TAXONOMY_KEYS if k not in sp_meta_keys]
        if missing_taxonomy:
            sp_missing.append("taxonomy")
        if sp_missing:
            missing["Species"] = sp_missing

        # Dataset metadata
        ds_missing = []
        if not ds.description:
            ds_missing.append("description")
        if not ds.platform:
            ds_missing.append("platform")
        if not ds.publication_id:
            ds_missing.append("publication")
        if ds_missing:
            missing["Dataset"] = ds_missing

        # Files
        file_missing = []
        if not ds._has_hdf5:
            file_missing.append("HDF5 (singlecell_umifrac)")
        present = {sf.type for sf in species.files.all()}
        for ft in SPECIES_FILE_TYPES:
            if ft not in present:
                file_missing.append(ft)
        if file_missing:
            missing["Files"] = file_missing

        return missing

    def render_missing_section(self, datasets):
        lines = ["## Missing data", ""]
        has_any_missing = False

        for ds in datasets:
            missing = ds._missing
            label = ds.internal_id or str(ds)
            if missing:
                has_any_missing = True
                lines.append(f"### {label} missing data")
                for category, items in missing.items():
                    lines.append(f"- **{category}**: {', '.join(items)}")
                lines.append("")

        if not has_any_missing:
            lines.append("Nothing missing.")
            lines.append("")

        return "\n".join(lines)

    def render_table_section(self, datasets):
        headers = ["Dataset", "Info", "MC", "SC", "MC.T", "CT", "GMods", "Expr", "Corr", "EC", "QC", "Sim", "Cytotrace", "Files"]

        rows = []
        for ds in datasets:
            missing = ds._missing
            has_info = not missing.get("Species") and not missing.get("Dataset")
            has_files = "Files" not in missing

            rows.append([
                ds.internal_id or "",
                self._sym(has_info),
                self._sym(ds._metacell_count),
                self._sym(ds._singlecell_count),
                self._sym(ds._metacelltype_count),
                self._sym(ds._celltype_count),
                self._sym(ds._genemodule_count),
                self._sym(ds._expression_count),
                self._sym(ds._correlation_count),
                self._sym(ds._conservation_count),
                self._sym(ds._qc_count),
                self._sym(ds._has_similarity),
                self._sym(ds._has_cytotrace),
                self._sym(has_files),
            ])

        return "## Summary\n\n" + self.render_table(headers, rows)

    def _sym(self, ok):
        if ok:
            return CHECK_COLOR if self._use_color else CHECK_PLAIN
        return CROSS_COLOR if self._use_color else CROSS_PLAIN

    def annotate_counts(self, datasets):
        """Bulk-annotate datasets with record counts."""
        ds_ids = [ds.id for ds in datasets]

        count_map = {
            "metacell": self._count_by_dataset(Metacell, ds_ids),
            "singlecell": self._count_by_dataset(SingleCell, ds_ids),
            "metacelltype": self._count_by_dataset(MetacellType, ds_ids),
            "celltype": self._count_by_dataset(CellType, ds_ids),
            "genemodule": self._count_by_dataset(GeneModule, ds_ids),
            "expression": self._count_by_dataset(MetacellGeneExpression, ds_ids),
            "correlation": self._count_by_dataset(GeneCorrelation, ds_ids),
            "qc": self._count_by_dataset(DatasetQualityControl, ds_ids),
        }

        conservation_counts = self._count_conservation(ds_ids)

        hdf5_ds_ids = set(
            DatasetFile.objects.filter(dataset_id__in=ds_ids, type="singlecell_umifrac").values_list(
                "dataset_id", flat=True
            )
        )

        similarity_ds_ids = self._check_similarity(ds_ids)

        cytotrace_ds_ids = set(
            Metacell.objects.filter(dataset_id__in=ds_ids, cytotrace__isnull=False)
            .values_list("dataset_id", flat=True)
            .distinct()
        )

        for ds in datasets:
            ds._metacell_count = count_map["metacell"].get(ds.id, 0)
            ds._singlecell_count = count_map["singlecell"].get(ds.id, 0)
            ds._metacelltype_count = count_map["metacelltype"].get(ds.id, 0)
            ds._celltype_count = count_map["celltype"].get(ds.id, 0)
            ds._genemodule_count = count_map["genemodule"].get(ds.id, 0)
            ds._expression_count = count_map["expression"].get(ds.id, 0)
            ds._correlation_count = count_map["correlation"].get(ds.id, 0)
            ds._qc_count = count_map["qc"].get(ds.id, 0)
            ds._conservation_count = conservation_counts.get(ds.id, 0)
            ds._has_hdf5 = ds.id in hdf5_ds_ids
            ds._has_similarity = ds.id in similarity_ds_ids
            ds._has_cytotrace = ds.id in cytotrace_ds_ids

        return datasets

    def _count_by_dataset(self, model, ds_ids):
        """Return {dataset_id: count} dict for a given model with a `dataset` FK."""
        field = model._meta.get_field("dataset").attname
        qs = model.objects.filter(dataset_id__in=ds_ids).values(field).annotate(cnt=Count("id"))
        return {row[field]: row["cnt"] for row in qs}

    def _count_conservation(self, ds_ids):
        """Count ExpressionConservation records where dataset or dataset2 matches."""
        as_dataset = (
            ExpressionConservation.objects.filter(dataset_id__in=ds_ids)
            .values("dataset_id")
            .annotate(cnt=Count("id"))
        )
        as_dataset2 = (
            ExpressionConservation.objects.filter(dataset2_id__in=ds_ids)
            .values("dataset2_id")
            .annotate(cnt=Count("id"))
        )
        counts = {}
        for row in as_dataset:
            counts[row["dataset_id"]] = counts.get(row["dataset_id"], 0) + row["cnt"]
        for row in as_dataset2:
            counts[row["dataset2_id"]] = counts.get(row["dataset2_id"], 0) + row["cnt"]
        return counts

    def _check_similarity(self, ds_ids):
        """Return set of dataset IDs that have all three similarity scores (pesci, samap, aucell)."""
        metacelltype_ids_by_ds = {}
        for row in MetacellType.objects.filter(dataset_id__in=ds_ids).values("id", "dataset_id"):
            metacelltype_ids_by_ds.setdefault(row["dataset_id"], []).append(row["id"])

        if not metacelltype_ids_by_ds:
            return set()

        all_mct_ids = set()
        for ids in metacelltype_ids_by_ds.values():
            all_mct_ids.update(ids)

        sims = MetacellTypeSimilarity.objects.filter(
            Q(metacelltype_id__in=all_mct_ids) | Q(metacelltype2_id__in=all_mct_ids)
        ).values("metacelltype_id", "metacelltype2_id", "samap_score", "aucell_1to2", "pesci_score")

        ds_has_samap = set()
        ds_has_pesci = set()
        ds_has_aucell = set()

        mct_to_ds = {}
        for ds_id, mct_ids in metacelltype_ids_by_ds.items():
            for mct_id in mct_ids:
                mct_to_ds[mct_id] = ds_id

        for sim in sims:
            ds_id = mct_to_ds.get(sim["metacelltype_id"]) or mct_to_ds.get(sim["metacelltype2_id"])
            if ds_id is None:
                continue
            if sim["samap_score"] is not None:
                ds_has_samap.add(ds_id)
            if sim["pesci_score"] is not None:
                ds_has_pesci.add(ds_id)
            if sim["aucell_1to2"] is not None:
                ds_has_aucell.add(ds_id)

        return ds_has_samap & ds_has_pesci & ds_has_aucell

    def _display_width(self, s):
        """Return the display width of a string, accounting for wide characters and ANSI codes."""
        text = re.sub(r"\033\[[0-9;]*m", "", str(s))
        w = 0
        for ch in text:
            eaw = unicodedata.east_asian_width(ch)
            w += 2 if eaw in ("W", "F") else 1
        return w

    def render_table(self, headers, rows):
        """Render markdown table."""
        col_widths = [self._display_width(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], self._display_width(cell))

        def pad(cell, width):
            """Pad cell to target display width."""
            cell_str = str(cell)
            return cell_str + " " * (width - self._display_width(cell_str))

        def fmt_row(cells):
            parts = [pad(cell, col_widths[i]) for i, cell in enumerate(cells)]
            return "| " + " | ".join(parts) + " |"

        lines = [fmt_row(headers), "| " + " | ".join("-" * w for w in col_widths) + " |"]
        lines.extend(fmt_row(row) for row in rows)
        return "\n".join(lines)
