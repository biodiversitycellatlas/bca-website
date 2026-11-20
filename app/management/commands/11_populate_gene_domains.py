"""Load Pfam domains from hmmscan --domtblout files."""

from gzip import open as gzip_open
from pathlib import Path

import yaml

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import Dataset, Domain, Gene


class Command(BaseCommand):
    """Load hmmscan domain annotations into genes."""

    help = "Load Pfam domains from all hmmscan --domtblout files."

    def add_arguments(self, parser):
        parser.add_argument("directory", type=Path, help="Directory containing hmmscan .domtblout files.")
        parser.add_argument(
            "--mapping-config",
            type=Path,
            required=True,
            help="YAML file mapping species IDs to gene annotation mapping files.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Parse files without modifying the database.")

    @transaction.atomic
    def handle(self, *args, **options):
        """Load domains."""
        directory = options["directory"]
        mapping_config = options["mapping_config"]
        dry_run = options["dry_run"]

        if not directory.is_dir():
            raise CommandError(f"Directory does not exist: {directory}")

        if not mapping_config.is_file():
            raise CommandError(f"Mapping config does not exist: {mapping_config}")

        files = sorted(directory.glob("*.domtblout"))

        if not files:
            raise CommandError(f"No *.domtblout files found in {directory}")

        # Load YAML configuration.
        try:
            with mapping_config.open() as handle:
                mappings = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            raise CommandError(f"Invalid YAML in {mapping_config}: {exc}") from exc

        if not isinstance(mappings, dict):
            raise CommandError(f"Mapping config must contain a YAML mapping: {mapping_config}")

        # Normalize species IDs to lower case
        mappings = { str(species_id).lower(): Path(mapping_path) for species_id, mapping_path in mappings.items() }

        total_hits = 0
        total_domains = 0
        total_relationships = 0

        # Cache all domains once
        domains = { domain.name.lower(): domain for domain in Domain.objects.all() }

        # Cache the through model so relationships can be bulk-created.
        gene_domain_through = Gene.domains.through

        # Cache parsed mapping files so the same mapping can be reused by
        # multiple species, e.g. clyhem01 and clyhem02.
        mapping_cache = {}

        for path in files:
            species_id = path.name.split("_", 1)[0]
            species_key = species_id.lower()

            # Find datasets whose internal_id starts with the species ID.
            datasets = list(Dataset.objects.select_related("species").filter(internal_id__istartswith=species_id))

            if not datasets:
                self.stderr.write(
                    self.style.WARNING(f"{path.name}: no dataset found with internal_id starting with {species_id!r}")
                )
                continue

            # All matching datasets should belong to the same species.
            species_ids = {dataset.species_id for dataset in datasets}

            if len(species_ids) > 1:
                raise CommandError(
                    f"{path.name}: datasets with internal_id starting "
                    f"with {species_id!r} belong to multiple species."
                )

            dataset = datasets[0]
            species = dataset.species
            self.stdout.write(f"{path.name}: {species.scientific_name}")

            # Skip the species if ANY gene already has at least one domain.
            if Gene.objects.filter(species=species, domains__isnull=False).exists():
                self.stdout.write("  Skipping: species already has at least one gene with domains.")
                continue

            # Load genes once for this species
            genes = { gene.name.lower(): gene for gene in Gene.objects.filter(species=species) }

            # Determine whether this species has a custom mapping
            mapping_path = next((path for key, path in mappings.items() if key.startswith(species_key)), None)
            gene_mapping = None

            if mapping_path is not None:
                if not mapping_path.is_absolute():
                    mapping_path = mapping_config.parent / mapping_path
                mapping_path = mapping_path.resolve()
                mapping_cache_key = str(mapping_path)

                if mapping_cache_key in mapping_cache:
                    gene_mapping = mapping_cache[mapping_cache_key]
                else:
                    if not mapping_path.is_file():
                        raise CommandError(f"{species_id}: mapping file does not exist: {mapping_path}")

                    gene_mapping = {}
                    try:
                        if mapping_path.suffix == ".gz":
                            handle = gzip_open(mapping_path, mode="rt", encoding="utf-8")
                        else:
                            handle = mapping_path.open(mode="r", encoding="utf-8")

                        with handle:
                            for line_number, line in enumerate(handle, start=1):
                                line = line.strip()

                                if not line:
                                    continue

                                fields = line.split("\t")
                                db_gene, file_gene, *_ = fields
                                gene_mapping[file_gene.lower()] = db_gene.lower()

                    except OSError as exc:
                        raise CommandError(f"Could not read mapping file {mapping_path}: {exc}") from exc

                    mapping_cache[mapping_cache_key] = gene_mapping

                self.stdout.write(f"  Using gene mapping: {mapping_path}")

            # This should normally be empty because of the species-level
            # check above, but keeping it makes the relationship logic safe.
            existing_relationships = set(
                gene_domain_through.objects.filter(gene__species=species,).values_list("gene_id", "domain_id")
            )

            file_hits = 0
            file_relationships = 0

            # Keep track of gene names found in the file for diagnostics.
            file_gene_names = []

            # Accumulate relationships and bulk-create them after parsing.
            new_relationships = []

            with path.open() as handle:
                for line_number, line in enumerate(handle, start=1):
                    line = line.strip()

                    # Skip comments and blank lines.
                    if not line or line.startswith("#"):
                        continue

                    fields = line.split()

                    # hmmscan --domtblout has 23 fixed columns,
                    # followed by the target description.
                    if len(fields) < 23:
                        self.stderr.write(
                            self.style.ERROR(
                                f"{path.name}:{line_number}: "
                                f"malformed line, expected at least "
                                f"23 fields, got {len(fields)}"
                            )
                        )
                        continue

                    target_name = fields[0]
                    target_accession = fields[1]
                    gene_name = fields[3]
                    description = " ".join(fields[22:])
                    file_gene_names.append(gene_name)

                    # Resolve the file gene to the DB gene.
                    if gene_mapping is not None:
                        db_gene_name = gene_mapping.get(gene_name.lower())
                        if db_gene_name is None:
                            continue

                        gene = genes.get(db_gene_name)
                    else:
                        gene = genes.get(gene_name.lower())

                        if gene is None and gene_name.endswith("-RA"):
                            gene_name = gene_name.removesuffix("-RA")
                            gene = genes.get(gene_name.lower())

                        if gene is None and "_" in gene_name:
                            stripped_gene_name = gene_name.split("_", 1)[1]
                            gene = genes.get(stripped_gene_name.lower())

                    if gene is None:
                        continue

                    file_hits += 1
                    if dry_run:
                        self.stdout.write(f"  {gene.name} -> {target_name} ({target_accession})")
                        continue

                    domain_key = target_name.lower()
                    domain = domains.get(domain_key)

                    if domain is None:
                        domain = Domain.objects.create(name=target_name, description=description)
                        domains[domain_key] = domain
                        total_domains += 1

                    elif not domain.description and description:
                        domain.description = description
                        domain.save(update_fields=["description"])

                    relationship_key = (gene.pk, domain.pk)
                    if relationship_key not in existing_relationships:
                        existing_relationships.add(relationship_key)
                        new_relationships.append(gene_domain_through(gene_id=gene.pk, domain_id=domain.pk))
                        file_relationships += 1

            # Bulk-create all relationships for this file.
            if not dry_run and new_relationships:
                gene_domain_through.objects.bulk_create(new_relationships, ignore_conflicts=True)

            # If nothing matched, show diagnostic samples.
            if file_hits == 0:
                db_gene_names = list(genes.values())
                db_sample = [gene.name for gene in db_gene_names[:6]]
                file_sample = file_gene_names[:6]

                self.stdout.write(self.style.WARNING(f"  DB genes (first 6): {', '.join(db_sample) or '(none)'}"))
                self.stdout.write(self.style.WARNING(f"  File genes (first 6): {', '.join(file_sample) or '(none)'}"))

            total_hits += file_hits
            total_relationships += file_relationships
            if file_hits == 0:
                self.stdout.write(self.style.ERROR("  No matched HMM hits!"))
            else:
                self.stdout.write(f"  {file_hits} matched HMM hits, {file_relationships} new gene-domain relationships.")

        if dry_run:
            transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {total_hits} matched HMM hits, "
                f"{total_domains} new domains, "
                f"{total_relationships} new relationships."
            )
        )
