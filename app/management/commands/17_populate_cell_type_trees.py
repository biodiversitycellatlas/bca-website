"""Populate cell type trees, nodes, and node markers from per-dataset files."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import CellTypeTree, CellTypeTreeNode, CellTypeTreeNodeMarker, Dataset, Gene

NEWICK_SUFFIX = ".bonsai_flattened_tree.nwk"
MARKERS_SUFFIX = ".node_markers.tsv"
SUPPORT_SUFFIX = ".node_support_expanded.tsv"

DEFAULT_COLOR = "#AAAAAA"

MARKERS_COLUMNS = ["p_val", "avg_log2FC", "pct.1", "pct.2", "p_val_adj", "gene", "focus_node"]
SUPPORT_COLUMNS = ["node", "color", "is_significant"]


class Command(BaseCommand):
    """Populate cell type trees from Newick, node support, and node marker files."""

    help = "Populate CellTypeTree, CellTypeTreeNode and CellTypeTreeNodeMarker data."

    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            "directory",
            type=Path,
            help="Directory containing the per-dataset input files.",
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

        newick_files = sorted(directory.glob(f"*{NEWICK_SUFFIX}"))

        if not newick_files:
            self.stdout.write(self.style.WARNING(f"No *{NEWICK_SUFFIX} files found in {directory}"))
            return

        totals = {"trees": 0, "nodes": 0, "markers": 0, "missing_genes": 0}

        for newick_file in newick_files:
            internal_id = newick_file.name.removesuffix(NEWICK_SUFFIX)
            stats = self.process_dataset(directory, internal_id, dry_run=dry_run)
            if stats is None:
                continue
            for key in totals:
                totals[key] += stats[key]

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Trees: {totals['trees']}, nodes: {totals['nodes']}, "
                f"markers: {totals['markers']}, missing genes: {totals['missing_genes']}"
            )
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no database changes were made."))

    def process_dataset(self, directory, internal_id, dry_run=False):
        """Process the three input files for a single dataset."""
        self.stdout.write(f"\nProcessing dataset: {internal_id}")

        dataset = self.get_dataset(internal_id)
        if dataset is None:
            return None

        newick_file = directory / f"{internal_id}{NEWICK_SUFFIX}"
        markers_file = directory / f"{internal_id}{MARKERS_SUFFIX}"
        support_file = directory / f"{internal_id}{SUPPORT_SUFFIX}"

        newick = self.read_newick(newick_file)
        if newick is None:
            return None

        if support_file.is_file():
            node_meta = self.read_node_support(support_file)
        else:
            self.stdout.write(self.style.WARNING(f"  {support_file.name} not found; no node metadata."))
            node_meta = {}

        if markers_file.is_file():
            marker_rows, missing_genes, missing_gene_names = self.read_node_markers(markers_file, dataset)
        else:
            self.stdout.write(self.style.WARNING(f"  {markers_file.name} not found; no markers."))
            marker_rows, missing_genes, missing_gene_names = [], 0, []

        node_names = set(node_meta) | {row["focus_node"] for row in marker_rows}

        self.stdout.write(f"  Newick length: {len(newick)}")
        self.stdout.write(f"  Nodes: {len(node_names)}")
        self.stdout.write(f"  Markers: {len(marker_rows)}")
        self.stdout.write(f"  Missing genes: {missing_genes}")

        if len(missing_gene_names) > 1:
            self.stdout.write(f"  Missing gene names from file (showing 6 of {len(missing_gene_names)}):")
            for name in missing_gene_names[:6]:
                self.stdout.write(f"    {name}")
            db_gene_names = list(
                Gene.objects.filter(species=dataset.species).order_by("id").values_list("name", flat=True)[:6]
            )
            self.stdout.write(f"  Gene names in database for {dataset.species} (showing up to 6):")
            if db_gene_names:
                for name in db_gene_names:
                    self.stdout.write(f"    {name}")
            else:
                self.stdout.write("    (none - no Gene rows for this species)")

        if dry_run:
            return {
                "trees": 1,
                "nodes": len(node_names),
                "markers": len(marker_rows),
                "missing_genes": missing_genes,
            }

        with transaction.atomic():
            # Idempotency: drop any existing tree for this dataset (cascades to nodes/markers).
            CellTypeTree.objects.filter(dataset=dataset).delete()

            tree = CellTypeTree.objects.create(dataset=dataset, newick=newick)
            nodes = self.create_nodes(tree, node_names, node_meta)
            created_markers = self.create_markers(marker_rows, nodes)

        return {
            "trees": 1,
            "nodes": len(nodes),
            "markers": created_markers,
            "missing_genes": missing_genes,
        }

    def get_dataset(self, internal_id):
        """Look up the dataset by internal_id, or None if it cannot be resolved."""
        try:
            return Dataset.objects.get(internal_id=internal_id)
        except Dataset.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"  Dataset with internal_id={internal_id!r} does not exist."))
            return None
        except Dataset.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR(f"  Multiple datasets found with internal_id {internal_id!r}."))
            return None

    def read_newick(self, path):
        """Read Newick tree from file."""
        if not path.is_file():
            self.stdout.write(self.style.ERROR(f"  {path.name} not found."))
            return None

        newick = path.read_text(encoding="utf-8").strip()

        if not newick:
            self.stdout.write(self.style.ERROR(f"  {path.name} is empty."))
            return None

        return newick

    def read_node_support(self, path):
        """Read node metadata, keeping the first row's color/significant per node."""
        rows = self.read_tsv(path, required=SUPPORT_COLUMNS)
        node_meta = {}

        for row in rows:
            node = row["node"]

            if not node or node in node_meta:
                continue

            node_meta[node] = {
                "color": row["color"] or DEFAULT_COLOR,
                "significant": self.parse_bool(row["is_significant"]),
            }

        return node_meta

    def read_node_markers(self, path, dataset):
        """Read marker rows and resolve gene names to Gene objects for the dataset species."""
        rows = self.read_tsv(path, required=MARKERS_COLUMNS)

        gene_names = {row["gene"] for row in rows if row["gene"]}
        # Also match the - -> _ variant, since some species store names with underscores.
        lookup_names = gene_names | {name.replace("-", "_") for name in gene_names}
        genes = {gene.name: gene for gene in Gene.objects.filter(species=dataset.species, name__in=lookup_names)}

        marker_rows = []
        missing_genes = 0
        missing_gene_names = []
        seen_missing = set()

        for row in rows:
            focus_node = row["focus_node"]
            gene = genes.get(row["gene"]) or genes.get(row["gene"].replace("-", "_"))

            if gene is None:
                missing_genes += 1
                if row["gene"] and row["gene"] not in seen_missing:
                    seen_missing.add(row["gene"])
                    missing_gene_names.append(row["gene"])
                continue

            if not focus_node:
                missing_genes += 1
                continue

            marker_rows.append(
                {
                    "focus_node": focus_node,
                    "gene": gene,
                    "p_value": float(row["p_val"]),
                    "q_value": float(row["p_val_adj"]),
                    "avg_log2fc": float(row["avg_log2FC"]),
                    "pct_1": float(row["pct.1"]),
                    "pct_2": float(row["pct.2"]),
                }
            )

        return marker_rows, missing_genes, missing_gene_names

    def create_nodes(self, tree, node_names, node_meta):
        """Create the tree's nodes and return a node-name to node mapping."""
        nodes = []

        for name in sorted(node_names):
            meta = node_meta.get(name, {"color": DEFAULT_COLOR, "significant": None})
            nodes.append(
                CellTypeTreeNode(
                    tree=tree,
                    node=name,
                    color=meta["color"],
                    significant=meta["significant"],
                )
            )

        CellTypeTreeNode.objects.bulk_create(nodes, batch_size=1000)

        # Re-fetch so the returned instances carry their primary keys for marker references.
        return {node.node: node for node in tree.nodes.all()}

    def create_markers(self, marker_rows, nodes):
        """Create the node marker records and return how many were created."""
        markers = []

        for row in marker_rows:
            node = nodes.get(row["focus_node"])

            if node is None:
                continue

            markers.append(
                CellTypeTreeNodeMarker(
                    node=node,
                    gene=row["gene"],
                    p_value=row["p_value"],
                    q_value=row["q_value"],
                    avg_log2fc=row["avg_log2fc"],
                    pct_1=row["pct_1"],
                    pct_2=row["pct_2"],
                )
            )

        if markers:
            CellTypeTreeNodeMarker.objects.bulk_create(markers, batch_size=10000)

        return len(markers)

    def read_tsv(self, path, required):
        """Read a TSV file into a list of dicts keyed by the required column names."""
        with path.open("r", encoding="utf-8") as handle:
            header = handle.readline().strip().split("\t")
            index = {name: i for i, name in enumerate(header)}

            missing = [column for column in required if column not in index]
            if missing:
                raise CommandError(f"{path.name}: missing required columns {missing}")

            rows = []
            for line in handle:
                line = line.strip()
                if not line:
                    continue

                fields = line.split("\t")
                rows.append(
                    {
                        column: (fields[index[column]].strip() if index[column] < len(fields) else "")
                        for column in required
                    }
                )

        return rows

    @staticmethod
    def parse_bool(value):
        """Parse an R-style TRUE/FALSE (or 1/0) value into a bool, or None if unknown."""
        value = value.strip().upper()
        if value in ("TRUE", "1", "YES"):
            return True
        if value in ("FALSE", "0", "NO"):
            return False
        return None
