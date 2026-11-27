# app/management/commands/load_orthogroups.py

import gzip
import re
from collections import defaultdict

import yaml
from django.core.management.base import BaseCommand, CommandError

from app.models import Dataset, Gene, Orthogroup, Ortholog, Species


class Command(BaseCommand):
    """Load orthogroups and orthologs from an orthology file."""

    help = "Load orthogroups and orthologs from an orthology file."

    BATCH_SIZE = 5000

    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument("file", help="Orthology file.")
        parser.add_argument("--mapping-config", help="YAML file containing dataset ID -> gene mapping TSV.")
        parser.add_argument("--dry-run", action="store_true", help="Match genes without modifying the database.")

    def handle(self, *args, **options):
        """Run the command."""
        filename = options["file"]
        mapping_config = options["mapping_config"]
        dry_run = options["dry_run"]

        self.stdout.write("Loading species...")
        species_by_prefix = self.load_species()

        valid_prefixes = sum(species is not None for species in species_by_prefix.values())
        self.stdout.write(f"Loaded {valid_prefixes:,} species prefixes.")
        self.stdout.write("Loading genes from database...")
        genes_by_species = self.load_existing_genes()

        total_genes = sum(len(index["exact"]) for index in genes_by_species.values())
        self.stdout.write(f"Loaded {total_genes:,} genes from {len(genes_by_species):,} species.")

        mappings_by_species = {}
        if mapping_config:
            mappings_by_species = self.load_mappings(mapping_config, genes_by_species)

        orthogroup_names = set()
        ortholog_rows = []
        missing = []
        malformed = 0

        self.stdout.write(f"Reading {filename}...")
        with self.open_text(filename) as handle:
            for line_number, raw_line in enumerate(handle, 1):
                line = raw_line.rstrip("\r\n")

                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t", 1)

                if len(parts) != 2:
                    malformed += 1
                    continue

                orthogroup_name = parts[0].strip()
                protein_names = parts[1].strip()

                if not orthogroup_name:
                    malformed += 1
                    continue

                orthogroup_names.add(orthogroup_name)

                for protein_name in protein_names.split():
                    protein_name = protein_name.strip()

                    if not protein_name:
                        continue

                    species = self.find_species(protein_name, species_by_prefix)

                    if species is None:
                        missing.append(
                            {
                                "line": line_number,
                                "orthogroup": orthogroup_name,
                                "protein": protein_name,
                                "reason": (
                                    "unknown or ambiguous "
                                    "species prefix"
                                ),
                            }
                        )
                        continue

                    gene_indexes = genes_by_species.get(species.id)
                    if gene_indexes is None:
                        missing.append(
                            {
                                "line": line_number,
                                "orthogroup": orthogroup_name,
                                "protein": protein_name,
                                "reason": (
                                    "species has no genes "
                                    "in database"
                                ),
                            }
                        )
                        continue

                    mapping = mappings_by_species.get(species.id)
                    gene = mapping.get(protein_name) if mapping is not None else None
                    if gene is None:
                        gene = self.find_gene(protein_name, gene_indexes, mappings_by_species)

                    if gene is None:
                        missing.append(
                            {
                                "line": line_number,
                                "orthogroup": orthogroup_name,
                                "protein": protein_name,
                                "reason": "gene not found",
                            }
                        )
                        continue

                    # This is the existing DB Gene object.
                    # It is never modified.
                    ortholog_rows.append((orthogroup_name, gene))

        self.stdout.write("")
        self.stdout.write("Results")
        self.stdout.write("=======")

        self.stdout.write(
            f"Orthogroups:       "
            f"{len(orthogroup_names):,}"
        )

        self.stdout.write(
            f"Matched orthologs: "
            f"{len(ortholog_rows):,}"
        )

        self.stdout.write(
            f"Missing genes:     "
            f"{len(missing):,}"
        )

        self.stdout.write(
            f"Malformed lines:   "
            f"{malformed:,}"
        )

        if missing:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"First {min(50, len(missing))} missing:"
                )
            )

            for item in missing[:50]:
                self.stdout.write(
                    f"  {item['protein']} "
                    f"({item['orthogroup']}, "
                    f"line {item['line']}: "
                    f"{item['reason']})"
                )

        if malformed:
            raise CommandError(
                f"Found {malformed} malformed lines."
            )

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: no database changes were made."
                )
            )
            return

        self.create_orthogroups(
            orthogroup_names
        )

        orthogroup_ids = dict(
            Orthogroup.objects.filter(
                name__in=orthogroup_names,
            ).values_list(
                "name",
                "id",
            )
        )

        # Unique (gene_id, orthogroup_id) pairs.
        ortholog_keys = set()

        for orthogroup_name, gene in ortholog_rows:
            orthogroup_id = orthogroup_ids.get(
                orthogroup_name
            )

            if orthogroup_id is None:
                raise CommandError(
                    f"Orthogroup {orthogroup_name!r} "
                    "was not created or found."
                )

            ortholog_keys.add(
                (
                    gene.id,
                    orthogroup_id,
                )
            )

        self.stdout.write(
            f"Unique ortholog pairs: "
            f"{len(ortholog_keys):,}"
        )

        if not ortholog_keys:
            self.stdout.write(
                self.style.WARNING(
                    "No orthologs to insert."
                )
            )
            return

        gene_ids = {
            gene_id
            for gene_id, _ in ortholog_keys
        }

        group_ids = {
            orthogroup_id
            for _, orthogroup_id in ortholog_keys
        }

        self.stdout.write(
            "Checking existing orthologs..."
        )

        existing_orthologs = set(
            Ortholog.objects.filter(
                gene_id__in=gene_ids,
                orthogroup_id__in=group_ids,
            ).values_list(
                "gene_id",
                "orthogroup_id",
            )
        )

        new_ortholog_keys = (
            ortholog_keys - existing_orthologs
        )

        self.stdout.write(
            f"New orthologs: "
            f"{len(new_ortholog_keys):,}"
        )

        if not new_ortholog_keys:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Finished loading orthogroups "
                    "and orthologs."
                )
            )
            return

        species_by_gene_id = {}

        for _, gene in ortholog_rows:
            species_by_gene_id[
                gene.id
            ] = gene.species_id

        new_orthologs = [
            Ortholog(
                species_id=species_by_gene_id[gene_id],
                gene_id=gene_id,
                orthogroup_id=orthogroup_id,
            )
            for gene_id, orthogroup_id
            in new_ortholog_keys
        ]

        self.insert_orthologs(
            new_orthologs
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Finished loading orthogroups "
                "and orthologs."
            )
        )

    # ------------------------------------------------------------------
    # Species
    # ------------------------------------------------------------------

    def load_species(self):
        """
        Build a case-insensitive orthology-prefix -> Species map.

        Prefixes come ONLY from Species.scientific_name.

        Example:

            Amphimedon queenslandica
                -> ampque
                -> aque
        """
        species_by_prefix = {}

        for species in Species.objects.only(
            "id",
            "scientific_name",
        ):
            prefixes = self.get_species_prefixes(
                species
            )

            for prefix in prefixes:
                prefix = prefix.lower()

                if prefix not in species_by_prefix:
                    species_by_prefix[prefix] = species
                    continue

                existing = species_by_prefix[prefix]

                if existing is None:
                    continue

                if existing.id == species.id:
                    continue

                self.stdout.write(
                    self.style.WARNING(
                        f"Species prefix '{prefix}' "
                        f"is ambiguous between "
                        f"{existing.scientific_name} "
                        f"and {species.scientific_name}; "
                        "prefix disabled."
                    )
                )

                species_by_prefix[prefix] = None

        return species_by_prefix

    @staticmethod
    def get_species_prefixes(species):
        """
        Return the six-character prefix and four-character shorthand.

        Example:

            Amphimedon queenslandica
                -> ampque
                -> aque
        """
        scientific_name = (
            species.scientific_name.strip()
        )

        parts = re.split(
            r"\s+",
            scientific_name,
        )

        if len(parts) < 2:
            return set()

        genus = re.sub(
            r"[^A-Za-z]",
            "",
            parts[0],
        )

        species_name = re.sub(
            r"[^A-Za-z]",
            "",
            parts[1],
        )

        if not genus or not species_name:
            return set()

        six_character = (
            genus[:3] + species_name[:3]
        ).lower()

        prefixes = {
            six_character
        }

        if len(six_character) == 6:
            prefixes.add(
                (
                    six_character[0]
                    + six_character[3:]
                ).lower()
            )

        return prefixes

    @staticmethod
    def find_species(
        protein_name,
        species_by_prefix,
    ):
        """
        Resolve species using ONLY the orthology ID prefix.

        Example:

            Aque_Aqu2.1.27427_001
            ^^^^
            species prefix
        """
        prefix = protein_name.split(
            "_",
            1,
        )[0].lower()

        return species_by_prefix.get(
            prefix
        )

    # ------------------------------------------------------------------
    # DB Genes
    # ------------------------------------------------------------------

    def load_existing_genes(self):
        """
        Load existing DB genes as immutable references.

        Gene.name is never modified or normalized.

        Only exact DB names are indexed.
        """
        exact_by_species = defaultdict(dict)

        queryset = Gene.objects.only(
            "id",
            "name",
            "species_id",
        )

        for gene in queryset.iterator():
            exact_by_species[
                gene.species_id
            ][gene.name] = gene

        return {
            species_id: {
                "exact": exact_genes,
            }
            for species_id, exact_genes
            in exact_by_species.items()
        }

    # ------------------------------------------------------------------
    # Gene matching
    # ------------------------------------------------------------------

    @classmethod
    def find_gene(cls, protein_name, gene_indexes, mapping,):
        """
        Find an existing DB Gene for an orthology identifier.

        Matching order:

            1. Exact orthology ID == DB Gene.name
            2. Exact orthology ID in mapping file
               -> DB Gene.name
            3. Normalized orthology candidates == DB Gene.name
        """
        db_genes = gene_indexes["exact"]

        # 1. Exact DB name.
        gene = db_genes.get(protein_name)

        if gene is not None:
            return gene

        # 2. Exact annotation mapping: orthology ID -> DB Gene
        if mapping:
            gene = mapping.get(protein_name)

            if protein_name == "Chem_rna-XM_067078818.1":
                print("  ----- hey", protein_name)

            if gene is not None:
                return gene

        # 3. Fallback transformations happen ONLY to the orthology ID.
        for candidate in cls.get_gene_candidates(
            protein_name
        ):
            if candidate == protein_name:
                continue

            gene = db_genes.get(
                candidate
            )

            if gene is not None:
                return gene

        return None

    @classmethod
    def get_gene_candidates(
        cls,
        protein_name,
    ):
        """
        Generate fallback DB-name candidates from an orthology ID.

        The DB Gene.name is NEVER transformed.

        Examples:

            Aque_Aqu2.1.27427_001

                -> Aque_Aqu2.1.27427_001
                -> Aque_Aqu2.1.27427
                -> Aqu2.1.27427

            Amil_Amillepora20282-RA

                -> Amil_Amillepora20282-RA
                -> Amil_Amillepora20282
                -> Amillepora20282
        """
        candidates = []
        seen = set()

        def add(value):
            if value and value not in seen:
                seen.add(value)
                candidates.append(value)

        add(protein_name)

        # Remove final suffix.
        without_suffix = (
            cls.remove_gene_suffix(
                protein_name
            )
        )

        add(without_suffix)

        # Remove species prefix.
        #
        # Do this to every candidate generated so far.
        for candidate in list(candidates):
            without_prefix = (
                cls.remove_species_prefix(
                    candidate
                )
            )

            add(without_prefix)

        return candidates

    @staticmethod
    def remove_gene_suffix(name):
        """
        Remove the final '.', '_' or '-' suffix.

        Examples:

            Aque_Aqu2.1.27427_001
                -> Aque_Aqu2.1.27427

            Amil_Amillepora20282-RA
                -> Amil_Amillepora20282

            Aurcoe_rna-Aco03997.1
                -> Aurcoe_rna-Aco03997
        """
        match = re.search(
            r"[._-][^._-]*$",
            name,
        )

        if match is None:
            return name

        return name[
            :match.start()
        ]

    @staticmethod
    def remove_species_prefix(name):
        """
        Remove the first underscore-delimited component.

        Examples:

            Aque_Aqu2.1.27427
                -> Aqu2.1.27427

            Amil_Amillepora20282
                -> Amillepora20282

        Only the orthology identifier is transformed.
        """
        if "_" not in name:
            return name

        _, remainder = name.split(
            "_",
            1,
        )

        return remainder or name

    # ------------------------------------------------------------------
    # Mapping files
    # ------------------------------------------------------------------

    def load_mappings(
        self,
        filename,
        genes_by_species,
    ):
        """
        Load mappings for each species.

        YAML:

            dataset_id: mapping.tsv

        The mapping TSV is:

            DB Gene name    Orthology annotation

        Example:

            XLOC_007733    Chem_rna-XM_067078818.1

        It becomes:

            {
                "Chem_rna-XM_067078818.1": <Gene XLOC_007733>
            }

        The DB Gene must already exist.
        """
        config = self.load_mapping_config(
            filename
        )

        mappings_by_species = {}
        loaded_species = set()

        for dataset_id, mapping_filename in config.items():
            try:
                dataset = Dataset.objects.select_related("species").get(internal_id=dataset_id)
            except Dataset.DoesNotExist as exc:
                raise CommandError(f"Dataset {dataset_id!r} from mapping config does not exist.") from exc

            species_id = dataset.species_id
            if species_id in loaded_species:
                self.stdout.write(
                    f"Skipping mapping for {dataset_id}: species {dataset.species} already has a mapping."
                )
                continue

            gene_indexes = genes_by_species.get(species_id)
            if gene_indexes is None:
                self.stdout.write(
                    self.style.WARNING(f"No DB genes found for {dataset.species}; skipping mapping {mapping_filename}.")
                )
                loaded_species.add(species_id)
                continue

            self.stdout.write(f"Loading mapping for {dataset.species} rom {mapping_filename}")

            mapping = self.load_mapping_file(mapping_filename, gene_indexes)
            mappings_by_species[species_id] = mapping
            loaded_species.add(species_id)
            self.stdout.write(f"  exact annotation mappings: {len(mapping):,}")
        return mappings_by_species

    def load_mapping_file(self, filename, gene_indexes):
        """Load a mapping TSV."""
        mapping = {}

        db_genes = gene_indexes["exact"]

        with self.open_text(filename) as handle:
            for line_number, raw_line in enumerate(handle, 1):
                line = raw_line.rstrip("\r\n")

                if (not line or line.startswith("#")):
                    continue

                parts = line.split("\t")

                if len(parts) < 2:
                    continue

                db_gene_name = parts[0].strip()
                annotation_name = parts[1].strip()
                if not db_gene_name or not annotation_name:
                    continue

                gene = db_genes.get(db_gene_name)
                if gene is None:
                    continue

                # Exact orthology/annotation identifier.
                existing = mapping.get(annotation_name)
                if existing is None:
                    mapping[annotation_name] = gene
                    continue

                # Same annotation points to two different DB genes.
                if existing.id != gene.id:
                    mapping[annotation_name] = None

        # Remove ambiguous mappings.
        mapping = {annotation: gene for annotation, gene in mapping.items() if gene is not None}
        return mapping


    # Orthogroups / Orthologs
    def create_orthogroups(self, orthogroup_names):
        """Create missing orthogroups in bulk."""
        if not orthogroup_names:
            return

        existing_names = set(Orthogroup.objects.filter(name__in=orthogroup_names).values_list("name", flat=True))
        new_names = (orthogroup_names - existing_names)
        self.stdout.write(f"Creating {len(new_names):,} orthogroups...")

        if not new_names:
            return

        Orthogroup.objects.bulk_create(
            [Orthogroup(name=name) for name in new_names],
            batch_size=self.BATCH_SIZE,
            ignore_conflicts=True,
        )

    def insert_orthologs(self, orthologs):
        """Insert orthologs in batches."""
        total = len(orthologs)

        if not total:
            return

        for start in range(0, total, self.BATCH_SIZE):
            batch = orthologs[start : start + self.BATCH_SIZE]
            Ortholog.objects.bulk_create(batch, batch_size=self.BATCH_SIZE, ignore_conflicts=True)
            processed = min(start + self.BATCH_SIZE, total)
            self.stdout.write(f"  inserted {processed:,}/{total:,}")

    # Config / files
    @staticmethod
    def load_mapping_config(filename):
        """Load the YAML mapping configuration."""
        try:
            with open(filename, encoding="utf-8") as handle:
                config = yaml.safe_load(handle)

        except OSError as exc:
            raise CommandError(f"Could not read mapping config {filename}: {exc}") from exc

        except yaml.YAMLError as exc:
            raise CommandError(f"Invalid YAML in {filename}: {exc}") from exc

        if not isinstance(config, dict):
            raise CommandError("Mapping config must be a YAML dictionary.")

        return config

    @staticmethod
    def open_text(filename):
        """Open a regular or gzip-compressed text file."""
        if str(filename).lower().endswith(".gz"):
            return gzip.open(filename, "rt", encoding="utf-8")

        return open(filename, "rt", encoding="utf-8")
