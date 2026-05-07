"""Compare gene modules."""

from itertools import chain

from rest import serializers
from rest.utils import group_by_key


class GeneModuleSimilarityService:
    """
    Compute gene module similarity.

    Handles:
    - Serializing genes
    - Computing overlaps within a dataset
    - Computing overlaps between datasets of the same species
    - Computing cross-species orthogroup overlaps
    - Building structured overlap results
    """

    def prepare_genes_info(self, modules):
        return {g.id: g for m in modules for g in m.genes.all()}

    def flat(self, d, keys):
        return list(chain.from_iterable(d.get(k, []) for k in keys))

    def list_shared_genes(
        self,
        dataset1,
        module1,
        unique1,
        dataset2,
        module2,
        unique2,
        shared,
        info,
        shared_split=None,
    ):
        groups = [
            (f"unique_{dataset1}_{module1}", dataset1, module1, unique1),
            (f"unique_{dataset2}_{module2}", dataset2, module2, unique2),
        ]

        if shared_split:
            im1, im2 = shared_split
            groups.extend(
                [
                    (f"shared_{dataset1}_{module1}", dataset1, module1, im1),
                    (f"shared_{dataset2}_{module2}", dataset2, module2, im2),
                ]
            )
        else:
            groups.append(("shared", None, None, shared))

        genes = []
        for overlap, dataset, module, group in groups:
            data = [info[g] for g in group if g in info]
            serialized = serializers.GeneNoSpeciesSerializer(data, many=True).data

            genes.extend(
                {
                    "overlap": overlap,
                    "dataset": dataset,
                    "module": module,
                    **g,
                }
                for g in serialized
            )

        return genes

    def calculate_similarity(
        self,
        dataset1,
        module1,
        unique1,
        dataset2,
        module2,
        unique2,
        shared,
        genes_info,
        shared_split=None,
    ):
        """
        Compute overlap statistics between two gene sets or modules.

        Args:
            genes_info: dict of gene_id → gene object

        Returns:
            dict of overlap stats, optionally with gene lists
        """
        unique1_count = len(unique1)
        unique2_count = len(unique2)
        shared_count = len(shared)
        union_count = unique1_count + unique2_count + shared_count

        # Calculate Jaccard similarity index
        jaccard = round(shared_count / union_count, 2) if union_count else 0

        # Split shared genes
        if shared_split:
            shared1, shared2 = shared_split
        else:
            shared1 = shared
            shared2 = shared
        shared1_count = len(shared1)
        shared2_count = len(shared2)

        results = {
            "dataset": dataset1,
            "module": module1,
            "dataset2": dataset2,
            "module2": module2,
            "similarity": jaccard,
            "shared_genes_module": shared1_count,
            "shared_genes_module2": shared2_count,
            "unique_genes_module": unique1_count,
            "unique_genes_module2": unique2_count,
        }
        return results

    def calculate_gene_similarity(self, d1, m1, m1_genes, d2, m2, m2_genes, genes_info, list_genes=False):
        """
        Compute overlap statistics between two gene modules.

        Args:
            d1 (str): Dataset 1 name.
            m1 (str): Module 1 name.
            m1_genes (set): Genes in first module.
            d2 (str): Dataset 2 name.
            m2 (str): Module 2 name.
            m2_genes (set): Genes in second module.
            genes_info (dict): Mapping of gene ID to gene object.
            list_genes (bool, optional): If True, return unique and shared genes.

        Returns:
            dict: Overlap statistics including similarity percentage,
            counts of unique/shared genes, and optionally gene lists.
        """
        unique1 = m1_genes - m2_genes
        unique2 = m2_genes - m1_genes
        shared = m1_genes & m2_genes

        fn = self.list_shared_genes if list_genes else self.calculate_similarity
        return fn(d1, m1, unique1, d2, m2, unique2, shared, genes_info)

    def calculate_orthogroup_similarity(self, d1, m1, orthogroups1, d2, m2, orthogroups2, genes_info, list_genes=False):
        """
        Compute overlap statistics between two modules using orthogroup mappings.

        Args:
            d1 (str): First dataset name.
            m1 (str): First module name.
            m1_orthogroups (dict): Mapping orthogroup → list of genes for module 1.
            d2 (str): Second dataset name.
            m2 (str): Second module name.
            m2_orthogroups (dict): Mapping orthogroup → list of genes for module 2.
            genes_info (dict): Mapping of gene ID to gene object.
            list_genes (bool, optional): If True, return unique and shared genes.

        Returns:
            dict: Overlap statistics based on orthogroups, including similarity
            percentage, counts of unique/shared genes, and optionally gene lists.
        """
        # Calculate shared orthogroups
        ogs1_set = orthogroups1.keys() - {None}
        ogs2_set = orthogroups2.keys() - {None}

        unique1_ogs = ogs1_set - ogs2_set
        unique2_ogs = ogs2_set - ogs1_set
        shared_ogs = ogs1_set & ogs2_set

        # Retrieve shared genes
        shared1 = self.flat(orthogroups1, shared_ogs)
        shared2 = self.flat(orthogroups2, shared_ogs)
        shared = shared1 + shared2

        # Retrieve unique genes including those without orthogroups
        unique1 = self.flat(orthogroups1, unique1_ogs) + list(orthogroups1.get(None, []))
        unique2 = self.flat(orthogroups2, unique2_ogs) + list(orthogroups2.get(None, []))

        # Remove duplicate genes and those from shared (e.g., multi-orthogroup genes)
        unique1 = list(set(unique1) - set(shared1))
        unique2 = list(set(unique2) - set(shared2))

        # Prepare arguments to run functions
        args = (
            d1,
            m1,
            unique1,
            d2,
            m2,
            unique2,
            shared,
            genes_info,
            (shared1, shared2),
        )

        fn = self.list_shared_genes if list_genes else self.calculate_similarity
        return fn(*args)

    def compare_modules(
        self,
        module_dict1,
        module_dict2,
        genes_info,
        similarity_fn,
        dataset1=None,
        dataset2=None,
        list_genes=False,
    ):
        # If module dictionaries are the same, avoid repeating calculations
        skip_duplicates = module_dict1 == module_dict2

        results = []
        for i, (m1, g1) in enumerate(module_dict1.items()):
            for j, (m2, g2) in enumerate(module_dict2.items()):
                if skip_duplicates and j <= i:  # skip same module and tested pairs
                    continue
                r = similarity_fn(dataset1.slug, m1, g1, dataset2.slug, m2, g2, genes_info, list_genes)
                results.append(r)

        return list(chain.from_iterable(results)) if list_genes else results

    def compare_within_dataset(self, dataset, module=None, module2=None, list_genes=False):
        """Compare pairwise gene overlaps within a dataset."""
        modules = dataset.gene_modules.prefetch_related("genes")
        module_genes = group_by_key(modules, "name", "genes")
        genes_info = self.prepare_genes_info(modules.all())

        # Filter module pairs if module/module2 specified
        if module and module2:
            filtered1 = {name: genes for name, genes in module_genes.items() if name in module}
            filtered2 = {name: genes for name, genes in module_genes.items() if name in module2}
        elif module:
            filtered1 = {name: genes for name, genes in module_genes.items() if name in module}
            filtered2 = filtered1
        else:
            filtered1 = module_genes
            filtered2 = filtered1

        return self.compare_modules(
            filtered1,
            filtered2,
            genes_info,
            self.calculate_gene_similarity,
            dataset,
            dataset,
            list_genes=list_genes,
        )

    def compare_within_species(self, dataset1, dataset2, module=None, module2=None, list_genes=False):
        """Compare pairwise gene overlaps between two datasets of the same species."""
        d1_modules = dataset1.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_genes = group_by_key(d1_modules, "name", "genes")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_genes = group_by_key(d2_modules, "name", "genes")

        genes_info = self.prepare_genes_info(list(d1_modules.all()) + list(d2_modules.all()))
        return self.compare_modules(
            d1_module_genes,
            d2_module_genes,
            genes_info,
            self.calculate_gene_similarity,
            dataset1,
            dataset2,
            list_genes,
        )

    def compare_across_species(self, dataset1, dataset2, module=None, module2=None, list_genes=False):
        """Compare pairwise orthogroup overlaps for each gene across species."""
        d1_modules = dataset1.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_orthogroups = group_by_key(d1_modules, "name", "genes__orthogroups", "genes")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_orthogroups = group_by_key(d2_modules, "name", "genes__orthogroups", "genes")

        modules = list(d1_modules.all()) + list(d2_modules.all())
        genes_info = self.prepare_genes_info(modules)

        return self.compare_modules(
            d1_module_orthogroups,
            d2_module_orthogroups,
            genes_info,
            self.calculate_orthogroup_similarity,
            dataset1,
            dataset2,
            list_genes,
        )

    def compare(self, dataset, dataset2, module, module2, list_genes):
        # Different comparison methods of gene module similarity
        if dataset == dataset2:
            overlaps = self.compare_within_dataset(dataset, module, module2, list_genes)
        elif dataset.species == dataset2.species:
            overlaps = self.compare_within_species(dataset, dataset2, module, module2, list_genes)
        else:
            overlaps = self.compare_across_species(dataset, dataset2, module, module2, list_genes)
        return overlaps
