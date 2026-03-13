"""REST API services logic."""

from itertools import combinations, chain

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

    def prepare_overlap_results(
        self,
        dataset1,
        module1,
        unique1,
        dataset2,
        module2,
        unique2,
        intersect,
        genes_info,
        list_genes=False,
        html=False,
        intersect_split=None,
    ):
        """
        Compute overlap statistics between two gene sets or modules.

        Args:
            genes_info: dict of gene_id → gene object
            list_genes: include serialized gene lists
            html: serialize with HTML links
            intersect_split: tuple of (intersect_genes1, intersect_genes2)

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

        if list_genes:
            return [g for g in map(genes_info.get, unique1) if g]

            results.update(
                {
                    "unique_genes_module_list": self.serialize_genes(unique1, genes_info, html),
                    "unique_genes_module2_list": self.serialize_genes(unique2, genes_info, html),
                    "intersecting_genes_list": self.serialize_genes(intersect, genes_info, html),
                }
            )
            if intersect_split:
                im1, im2 = intersect_split
                results["intersecting_genes_module_list"] = self.serialize_genes(im1, genes_info, html)
                results["intersecting_genes_module2_list"] = self.serialize_genes(im2, genes_info, html)

        return results

    def serialize_genes(self, ids, info, html=False):
        """
        Serialize gene objects from a list of IDs.

        Args:
            ids (list): List of gene IDs.
            info (dict): Mapping of gene ID to gene object.
            html (bool, optional): If True, return HTML code with links to objects.

        Returns:
            list: Serialized gene data.
        """
        genes = [g for g in map(info.get, ids) if g]
        s = serializers.GeneTableSerializer if html else serializers.GeneSerializer
        return s(genes, many=True).data

    def compute_gene_overlap(self, dataset, m1, m1_genes, m2, m2_genes, genes_info, list_genes=False, html=False):
        """
        Compute overlap statistics between two gene modules.

        Args:
            dataset (str): Dataset name.
            m1 (str): First module name.
            m1_genes (set): Genes in first module.
            m2 (str): Second module name.
            m2_genes (set): Genes in second module.
            genes_info (dict): Mapping of gene ID to gene object.
            list_genes (bool, optional): If True, include serialized gene lists
                for unique and intersecting genes.
            html (bool, optional): If True, return HTML code with links to objects.

        Returns:
            dict: Overlap statistics including similarity percentage,
            counts of unique/intersecting genes, and optionally gene lists.
        """
        unique1 = m1_genes - m2_genes
        unique2 = m2_genes - m1_genes
        intersect = m1_genes & m2_genes

        return self.prepare_overlap_results(
            dataset, m1, unique1, dataset, m2, unique2, intersect, genes_info, list_genes, html
        )

    def compare_within_dataset(self, dataset, module=None, module2=None, list_genes=False, html=False):
        """Compare pairwise gene overlaps within a dataset."""
        modules = dataset.gene_modules.prefetch_related("genes")
        module_genes = group_by_key(modules, "name", "genes")
        genes_info = self.prepare_genes_info(modules.all())

        # Calculate for each unique combination (avoid calculating overlaps twice)
        overlaps = []
        pairs = combinations(module_genes.items(), 2)

        for (m1, m1_genes), (m2, m2_genes) in pairs:
            if module and module not in (m1, m2):
                continue
            elif module2 and module2 not in (m1, m2):
                continue

            o = self.compute_gene_overlap(dataset, m1, m1_genes, m2, m2_genes, genes_info, list_genes, html)
            overlaps.append(o)
        return overlaps

    def compare_within_species(self, dataset, dataset2, module=None, module2=None, list_genes=False, html=False):
        """Compare pairwise gene overlaps between two datasets of the same species."""
        d1_modules = dataset.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_genes = group_by_key(d1_modules, "name", "genes")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_genes = group_by_key(d2_modules, "name", "genes")

        modules = list(d1_modules.all()) + list(d2_modules.all())
        genes_info = self.prepare_genes_info(modules)

        overlaps = []
        for m1, m1_genes in d1_module_genes.items():
            for m2, m2_genes in d2_module_genes.items():
                o = self.compute_gene_overlap(dataset, m1, m1_genes, m2, m2_genes, genes_info, list_genes, html)
                overlaps.append(o)
        return overlaps

    def compute_orthogroup_overlap(
        self, d1, m1, orthogroups1, d2, m2, orthogroups2, genes_info, list_genes=False, html=False
    ):
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
            list_genes (bool, optional): If True, include serialized gene lists
                for unique and intersecting genes. Defaults to False.
            html (bool, optional): If True, return HTML code with links to objects.

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

        return self.prepare_overlap_results(
            d1, m1, unique1, d2, m2, unique2, shared, genes_info, list_genes, html, (shared1, shared2)
        )

    def compare_across_species(self, dataset, dataset2, module=None, module2=None, list_genes=False, html=False):
        """Compare pairwise orthogroup overlaps for each gene across species."""
        d1_modules = dataset.gene_modules.prefetch_related("genes")
        if module:
            d1_modules = d1_modules.filter(name=module)
        d1_module_orthogroups = group_by_key(d1_modules, "name", "genes__orthogroup", "genes")

        d2_modules = dataset2.gene_modules.prefetch_related("genes")
        if module2:
            d2_modules = d2_modules.filter(name=module2)
        d2_module_orthogroups = group_by_key(d2_modules, "name", "genes__orthogroup", "genes")

        modules = list(d1_modules.all()) + list(d2_modules.all())
        genes_info = self.prepare_genes_info(modules)

        overlaps = []
        for m1, m1_orthogroups in d1_module_orthogroups.items():
            for m2, m2_orthogroups in d2_module_orthogroups.items():
                o = self.compute_orthogroup_overlap(
                    dataset, m1, m1_orthogroups, dataset2, m2, m2_orthogroups, genes_info, list_genes, html
                )
                overlaps.append(o)
        return overlaps

    def compare(self, dataset, dataset2, module, module2, list_genes, html):
        # Different comparison methods of gene module similarity
        if dataset == dataset2:
            overlaps = self.compare_within_dataset(dataset, module, module2, list_genes, html)
        elif dataset.species == dataset2.species:
            overlaps = self.compare_within_species(dataset, dataset2, module, module2, list_genes, html)
        else:
            overlaps = self.compare_across_species(dataset, dataset2, module, module2, list_genes, html)
        return overlaps
