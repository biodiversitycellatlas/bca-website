# app/management/commands/load_gene_lists.py

from pathlib import Path
import gzip
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import Dataset, Gene, GeneList


# Filename prefix -> GeneList.name
GENELIST_LOOKUP = {
    "adh": "Adhesion",
    "chr": "Chromatin",
    "cil": "cilia",
    "cyc": "Cyclins",
    "ion": "Ion channels",
    "rbp": "RNA-binding proteins",
    "sig": "Signalling",
    "tfs": "Transcription factors",
}


class Command(BaseCommand):
    help = "Load gene-list memberships from *.genes.list files."

    def add_arguments(self, parser):
        parser.add_argument("directory", type=Path, help="Directory containing *.genes.list files.")
        parser.add_argument(
            "--mapping-config",
            type=Path,
            required=True,
            help="YAML file containing dataset -> annotation mapping files.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and report results without modifying the database.",
        )

    def handle(self, *args, **options):
        directory = options["directory"]
        mapping_config = options["mapping_config"]
        dry_run = options["dry_run"]

        if not directory.is_dir():
            self.stderr.write(self.style.ERROR(f"Directory does not exist: {directory}"))
            return

        # Load mapping configuration
        mapping = self.load_mapping_config(mapping_config)
        files = sorted(directory.glob("*.genes.list"))
        if not files:
            self.stdout.write(self.style.WARNING(f"No *.genes.list files found in {directory}"))
            return

        self.stdout.write(f"Found {len(files)} gene-list files.")

        # Cache all objects we need up front.
        genelist_cache = {
            genelist.name: genelist
            for genelist in GeneList.objects.all()
        }

        dataset_cache = self.build_dataset_cache()

        # Cache genes by (species_id, gene_name).
        gene_cache = self.build_gene_cache()

        for path in files:
            self.process_file(
                path=path,
                mapping=mapping,
                genelist_cache=genelist_cache,
                dataset_cache=dataset_cache,
                gene_cache=gene_cache,
                dry_run=dry_run,
            )

    # Configuration
    @staticmethod
    def load_mapping_config(path):
        """Load dataset -> annotation mapping configuration."""
        import yaml

        with path.open() as handle:
            config = yaml.safe_load(handle) or {}

        return config

    # Caches
    def build_dataset_cache(self):
        """Build lookup from the gene prefix to a Dataset."""
        cache = {}
        datasets = Dataset.objects.select_related("species").all()
        for dataset in datasets:
            internal_id = dataset.internal_id

            if not internal_id:
                continue

            # The dataset internal ID is:
            #   6-char species prefix + 2-char dataset suffix
            species_prefix = internal_id[:6]

            # Normal 6-character lookup
            cache.setdefault(species_prefix.lower(), dataset)

            # 4-character lookup: Acrmil -> Amil
            prefix4 = species_prefix[0] + species_prefix[3:]

            cache.setdefault(prefix4.lower(), dataset)

        return cache

    def build_gene_cache(self):
        """Load genes into memory."""

        cache = {}
        genes = Gene.objects.all().only("id", "species_id", "name")
        for gene in genes:
            cache[(gene.species_id, gene.name)] = gene
        return cache

    # File processing
    def process_file(self, path, mapping, genelist_cache, dataset_cache, gene_cache, dry_run):
        """
        Process one *.genes.list file.

        Each file is committed independently.
        """

        filename = path.name
        genelist = self.get_genelist_from_filename(filename, genelist_cache)
        if genelist is None:
            self.stdout.write(self.style.WARNING(f"{filename}: skipped (unknown gene list)"))
            return

        # Determine the dataset from the first gene.
        #
        # All genes in one file are expected to belong to the same
        # dataset/species prefix.
        dataset = None

        # Relationships to create.
        memberships = []

        total = 0
        found = 0
        missing = 0

        # Cache mapping files per dataset.
        mapping_cache = {}

        with self.open_text_file(path) as handle:
            for line in handle:
                gene_name = line.strip()

                if not gene_name:
                    continue

                total += 1

                # Determine dataset from the original gene ID.
                if dataset is None:
                    dataset = self.find_dataset(gene_name, dataset_cache)

                    if dataset is None:
                        # We don't print individual missing genes.
                        missing += 1
                        continue

                # Apply annotation mapping if one exists for this dataset.
                source_gene_name = self.map_gene_name(
                    gene_name,
                    dataset=dataset,
                    mapping=mapping,
                    mapping_cache=mapping_cache
                )

                # Find the gene
                gene = self.find_gene(source_gene_name, dataset.species_id, gene_cache)

                if gene is None:
                    missing += 1
                    continue

                found += 1
                memberships.append((gene.id, genelist.id))

        # Commit this file independently.
        if not dry_run and memberships:
            with transaction.atomic():
                self.insert_memberships(memberships)

        processed = len(memberships)
        summary = (f"{filename}: {found}/{total} found, {processed} processed, {missing} missing")
        if missing:
            self.stdout.write(self.style.ERROR(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

    # Gene list
    @staticmethod
    def get_genelist_from_filename(filename, genelist_cache):
        """Get GeneList from filename."""

        prefix = filename.split(".", 1)[0]

        genelist_name = GENELIST_LOOKUP.get(prefix)

        if genelist_name is None:
            return None

        return genelist_cache.get(genelist_name)

    # Dataset lookup
    @staticmethod
    def find_dataset(gene_name, dataset_cache):
        """Find Dataset from gene prefix."""
        prefix = gene_name.split("_", 1)[0]
        return dataset_cache.get(prefix.lower())

    # Mapping
    def map_gene_name(self, gene_name, dataset, mapping, mapping_cache):
        """Convert source gene ID into the gene ID used in the DB."""

        dataset_key = dataset.internal_id

        if dataset_key not in mapping:
            return gene_name

        mapping_file = mapping[dataset_key]

        if not mapping_file:
            return gene_name

        if dataset_key not in mapping_cache:
            mapping_cache[dataset_key] = self.load_mapping_file(mapping_file)

        return mapping_cache[dataset_key].get(gene_name, gene_name)

    @staticmethod
    def load_mapping_file(path):
        """Load a two-column mapping file."""

        path = Path(path)
        result = {}

        if not path.exists():
            raise FileNotFoundError(f"Mapping file does not exist: {path}")

        if path.suffix == ".gz":
            opener = gzip.open
        else:
            opener = open

        with opener(path, "rt") as handle:
            for line in handle:
                line = line.rstrip("\n")

                if not line:
                    continue

                fields = line.split("\t")
                if len(fields) < 2:
                    continue

                db_gene, source_gene = fields[:2]
                db_gene = db_gene.strip()
                source_gene = source_gene.strip()
                if db_gene and source_gene:
                    result[source_gene] = db_gene

        return result

    # Gene matching
    @staticmethod
    def find_gene(gene_name, species_id, gene_cache):
        """Find a Gene using the requested fallback order."""

        # 1. Exact match
        gene = gene_cache.get((species_id, gene_name))
        if gene is not None:
            return gene

        # 2. Remove final suffix once.
        stripped = re.sub(r"[-_.][^-_.]+$", "", gene_name)

        if stripped != gene_name:
            gene = gene_cache.get((species_id, stripped))

            if gene is not None:
                return gene

        # 3. Remove prefix through underscore
        if "_" in gene_name:
            stripped = gene_name.split("_", 1)[1]
            gene = gene_cache.get((species_id, stripped))
            if gene is not None:
                return gene

            # Try suffix-stripped version
            stripped_suffix = re.sub(r"[-_.][^-_.]+$", "", stripped)
            if stripped_suffix != stripped:
                gene = gene_cache.get((species_id, stripped_suffix))

                if gene is not None:
                    return gene

        return None

    # Database insertion
    @staticmethod
    def insert_memberships(memberships):
        """Insert relationships directly into the through table."""

        through = Gene.genelists.through
        objects = [through(gene_id=gene_id, genelist_id=genelist_id) for gene_id, genelist_id in memberships]
        if not objects:
            return

        through.objects.bulk_create(objects, ignore_conflicts=True, batch_size=5000)

    # ----------------------------------------------------------------------
    # File handling
    # ----------------------------------------------------------------------

    @staticmethod
    def open_text_file(path):
        """Open plain or gzipped text file."""

        if path.suffix == ".gz":
            return gzip.open(path, "rt")

        return path.open("r")
