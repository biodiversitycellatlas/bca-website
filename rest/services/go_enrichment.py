"""GO term enrichment analysis."""

import gzip
import random
import math

from goatools.base import download_go_basic_obo, download_ncbi_associations
from goatools.obo_parser import GODag
from goatools.go_enrichment import GOEnrichmentStudy
from goatools.semantic import TermCounts, get_info_content, semantic_similarity
from goatools.gosubdag.gosubdag import GoSubDag


class GeneOntologyEnrichmentService:
    """Analyse GO term enrichment."""

    def read_emapper(self, f):
        """Read eggnog-mapper output."""
        gene2go = {}
        with gzip.open(f, "rt", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#"):
                    continue

                (
                    gene,
                    seed_ortholog,
                    evalue,
                    score,
                    eggnog_ogs,
                    max_annot_lvl,
                    cog_category,
                    description,
                    name,
                    gos,
                    ec,
                    kegg_ko,
                    kegg_pathway,
                    kegg_module,
                    kegg_reaction,
                    kegg_rclass,
                    brite,
                    kegg_tc,
                    cazy,
                    bigg_reaction,
                    pfams
                ) = line.rstrip().split("\t")
                gene2go[gene] = set(gos.split(","))
        return(gene2go)

    def run(self, obo_path, annotation_path, query_genes, background_genes=None, methods=["bonferroni"], qvalue=0.05, load_obsolete=False):
        # Read input files
        obodag = GODag(obo_path, load_obsolete=load_obsolete)
        gene2go = self.read_emapper(annotation_path)

        if background_genes is None:
             background_genes = set(gene2go.keys())

        # Run enrichment test
        gostudy = GOEnrichmentStudy(background_genes, gene2go, obodag, methods=methods, alpha=qvalue)
        results = gostudy.run_study(query_genes)

        # Keep only significant terms
        results = [r for r in results if r.p_bonferroni <= qvalue]

        # Add level and parents from ontology
        for r in results:
            r.parents = [i.id for i in r.goterm.parents]

        reduced, sim_matrix = self.prune(results, obodag)
        dist_matrix = self.create_distance_matrix(reduced, sim_matrix)

        coords = MDS(
            n_components=2,
            dissimilarity="precomputed",
            random_state=0
        ).fit_transform(dist_matrix)

        return reduced, coords

    def create_distance_matrix(self, results, sim_matrix):
        n = len(results)
        gos = [r.GO for r in results]
        #dist_matrix = np.zeros((n, n))
        dist_matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            go_i = gos[i]
            for j in range(i + 1, n):
                go_j = gos[j]
                key = tuple(sorted((go_i, go_j)))
                dist = 1 - (sim_matrix.get(key) or 0)
                dist_matrix[i][j] = dist
                dist_matrix[j][i] = dist

        return dist_matrix

    def _prune_parent_child_GO_terms(self, go_parent, go_child, overlap_cutoff=0.75):
        is_enrichment = go_parent.enrichment == "e"
        overlap_ratio = go_child.study_count / go_parent.study_count

        # Discard parent if most genes are available in child
        if is_enrichment and overlap_ratio >= overlap_cutoff:
            discard = go_parent
            reason = f"redundant parent (genes enriched: {go_child.study_count}/{go_parent.study_count})"
        elif not is_enrichment and overlap_ratio < (1 - overlap_cutoff):
            discard = go_parent
            reason = f"redundant parent (genes depleted: {go_child.study_count}/{go_parent.study_count})"
        else:
            discard = go_child
            reason = f"redundant child (overlapping genes: {go_child.study_count}/{go_parent.study_count})"
        return discard, reason

    def prune(self, results, obodag, sim_cutoff=0.7, freq_cutoff=0.05, seed=42, ci=0.1):
        """
        Prune GO terms similar to REVIGO.

        Args:
            results (list): GO enrichment objects with GO, parents, pop_count, p_bonferroni.
            obodag (GODag): Full ontology.
            sim_cutoff (float): Max pairwise semantic similarity.
            freq_cutoff (float): Frequency threshold for removal.
            seed (int): Random seed.

        Returns:
            list[str]: Pruned GO IDs.
        """
        random.seed(seed)

        # Compute GO similarity matrix (upper triangle)
        n = len(results)
        discarded_gos = set()
        sim_matrix = {}

        for i in range(n):
            go_i = results[i]
            for j in range(i+1, n):
                go_j = results[j]

                # Calculate and cache semantic similarity value
                key = tuple(sorted((go_i.GO, go_j.GO)))
                if key not in sim_matrix:
                    try:
                        sim_matrix[key] = semantic_similarity(go_i.GO, go_j.GO, obodag)
                    except ValueError:
                        sim_matrix[key] = 0
                    s = sim_matrix[key]

                # Skip redundancy checks for this pair of GO terms
                if (
                    s is None or s < sim_cutoff or
                    go_i.goterm.level <= 3 or go_j.goterm.level <= 3 or
                    go_i in discarded_gos or go_j in discarded_gos
                ):
                    continue

                # Remove GO terms according to REVIGO rules (Supek et al., 2011)
                is_go_i_freq = go_i.pop_count / go_i.pop_n > freq_cutoff
                is_go_j_freq = go_j.pop_count / go_j.pop_n > freq_cutoff

                go_i_abs_log_prop = abs(math.log10(max(go_i.p_bonferroni, 1e-300)))
                go_j_abs_log_prop = abs(math.log10(max(go_j.p_bonferroni, 1e-300)))
                go_sum_abs_log_prop = go_i_abs_log_prop + go_j_abs_log_prop
                relative_change = 0 if go_sum_abs_log_prop == 0 else abs(go_i_abs_log_prop - go_j_abs_log_prop) / (go_sum_abs_log_prop / 2)
                significant_change = relative_change >= ci

                # Remove if one of the terms has broad interpretation (freq > 0.05)
                discard = None
                if is_go_i_freq and not is_go_j_freq:
                    discard = go_i
                    reason = "high freq i"
                elif not is_go_i_freq and is_go_j_freq:
                    discard = go_j
                    reason = "high freq j"
                # Remove term with less significant p-value
                elif significant_change and go_i_abs_log_prop > go_j_abs_log_prop:
                    discard = go_i
                    reason = f"lower pval i ({go_i_abs_log_prop} vs {go_j_abs_log_prop})"
                elif significant_change and go_i_abs_log_prop < go_j_abs_log_prop:
                    discard = go_j
                    reason = f"lower pval j ({go_i_abs_log_prop} vs {go_j_abs_log_prop})"
                # Remove parent or child term if they are in parent-child relationship
                elif go_j.GO in (parent.id for parent in go_i.goterm.parents):
                    go_parent = go_j
                    go_child = go_i
                    discard, reason = self._prune_parent_child_GO_terms(go_parent, go_child)
                elif go_i.GO in (parent.id for parent in go_j.goterm.parents):
                    go_parent = go_i
                    go_child = go_j
                    discard, reason = self._prune_parent_child_GO_terms(go_parent, go_child)
                # Remove first term (deterministic tie-breaker)
                else:
                    discard = random.choice([go_i, go_j])
                    reason = "randomness"

                discarded_gos.add(discard)
                if go_i in discarded_gos:
                    break

            reduced = set(results) - discarded_gos
        return reduced, sim_matrix
