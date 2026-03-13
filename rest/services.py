"""REST API services logic."""

from itertools import chain

from . import serializers
from .utils import group_by_key


class GeneModuleSimilarityService:
    """
    Service class to compute gene module similarity.

    Handles:
    - Serializing genes
    - Computing overlaps within a dataset
    - Computing overlaps between datasets of the same species
    - Computing cross-species orthogroup overlaps
    - Building structured overlap results
    """

    def prepare_genes_info(self, modules):
        return {g.id: g for m in modules for g in m.genes.all()}

    def list_shared_genes(
        self,
        dataset1,
        module1,
        unique1,
        dataset2,
        module2,
        unique2,
        intersect,
        info,
        intersect_split=None,
    ):
        all_groups = [("unique_module", unique1), ("unique_module2", unique2)]

        if intersect_split:
            im1, im2 = intersect_split
            all_groups.extend([("shared_module", im1), ("shared_module2", im2)])
        else:
            all_groups.extend([("shared", intersect)])

        genes = [
            {"overlap": cat, **g_data}
            for cat, group in all_groups
            for g_data in serializers.GeneSerializer([info[g] for g in group if info.get(g)], many=True).data
        ]
        return genes

    def calculate_similarity(
        self,
        dataset1,
        module1,
        unique1,
        dataset2,
        module2,
        unique2,
        intersect,
        genes_info,
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
        intersect_count = len(intersect)
        union_count = len(unique1) + len(unique2) + intersect_count

        # Calculate Jaccard similarity index
        jaccard = round(intersect_count / union_count * 100) if union_count else 0

        results = {
            "dataset": dataset1,
            "module": module1,
            "dataset2": dataset2,
            "module2": module2,
            "similarity": jaccard,
            "intersecting_genes": intersect_count,
            "unique_genes_module": len(unique1),
            "unique_genes_module2": len(unique2),
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
            counts of unique/intersecting genes, and optionally gene lists.
        """
        unique1 = m1_genes - m2_genes
        unique2 = m2_genes - m1_genes
        intersect = m1_genes & m2_genes

        fn = self.list_shared_genes if list_genes else self.calculate_similarity
        return fn(d1, m1, unique1, d2, m2, unique2, intersect, genes_info)

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
            percentage, counts of unique/intersecting genes, and optionally gene lists.
        """
        # Calculate intersecting orthogroups
        ogs1_set = orthogroups1.keys() - {None}
        ogs2_set = orthogroups2.keys() - {None}

        unique1_ogs = ogs1_set - ogs2_set
        unique2_ogs = ogs2_set - ogs1_set
        shared_ogs = ogs1_set & ogs2_set

        # Retrieve corresponding genes
        unique1 = list(chain.from_iterable(orthogroups1.get(i, []) for i in unique1_ogs))
        unique1 += list(orthogroups1.get(None, []))  # include genes without orthogroups
        unique2 = list(chain.from_iterable(orthogroups2.get(i, []) for i in unique2_ogs))
        unique2 += list(orthogroups2.get(None, []))  # include genes without orthogroups
        shared1 = list(chain.from_iterable(orthogroups1.get(i, []) for i in shared_ogs))
        shared2 = list(chain.from_iterable(orthogroups2.get(i, []) for i in shared_ogs))
        shared = shared1 + shared2

        args = (d1, m1, unique1, d2, m2, unique2, shared, genes_info)
        if list_genes:
            args += ((shared1, shared2),)
        fn = self.list_shared_genes if list_genes else self.calculate_similarity
        return fn(*args)

    def compare_modules(
        self, module_dict1, module_dict2, genes_info, similarity_fn, dataset1=None, dataset2=None, list_genes=False
    ):
        results = [
            similarity_fn(dataset1, m1, g1, dataset2, m2, g2, genes_info, list_genes)
            for m1, g1 in module_dict1.items()
            for m2, g2 in module_dict2.items()
        ]
        return list(chain.from_iterable(results)) if list_genes else list(results)

    def compare_within_dataset(self, dataset, module=None, module2=None, list_genes=False):
        """Compare pairwise gene overlaps within a dataset."""
        modules = dataset.gene_modules.prefetch_related("genes")
        module_genes = group_by_key(modules, "name", "genes")
        genes_info = self.prepare_genes_info(modules.all())

        # Filter module pairs if module/module2 specified
        if module or module2:
            filtered = {name: genes for name, genes in module_genes.items() if name in (module, module2)}
        else:
            filtered = module_genes

        return self.compare_modules(
            filtered, filtered, genes_info, self.calculate_gene_similarity, dataset, dataset, list_genes=list_genes
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
            d1_module_genes, d2_module_genes, genes_info, self.calculate_gene_similarity, dataset1, dataset2, list_genes
        )

    def compare_across_species(self, dataset1, dataset2, module=None, module2=None, list_genes=False):
        """Compare pairwise orthogroup overlaps for each gene across species."""
        d1_modules = dataset1.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_orthogroups = group_by_key(d1_modules, "name", "genes__orthogroup", "genes")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_orthogroups = group_by_key(d2_modules, "name", "genes__orthogroup", "genes")

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
