"""GO and Pfam enrichment analysis."""

import gzip
import random
import math
from collections import Counter

from scipy.stats import fisher_exact
from sklearn.manifold import MDS

from goatools.obo_parser import GODag
from goatools.go_enrichment import GOEnrichmentStudy
from goatools.semantic import semantic_similarity

import logging

logger = logging.getLogger(__name__)


def read_emapper(f):
    """Read eggnog-mapper output into gene annotations.

    Returns:
        tuple[dict[str, set[str]], dict[str, set[str]]]: Gene to GO terms
        and gene to Pfam domains.
    """
    gene2go = {}
    gene2pfam = {}
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
                kegg_brite,
                kegg_tc,
                cazy,
                bigg_reaction,
                pfams,
            ) = line.rstrip().split("\t")
            gene2go[gene] = {g for g in gos.split(",") if g and g != "-"}
            gene2pfam[gene] = {p for p in pfams.split(",") if p and p != "-"}
    return gene2go, gene2pfam


class GeneOntologyEnrichmentService:
    """Analyze GO enrichment."""

    seed = 42  # Consistent results

    def __init__(
        self,
        obo_path,
        annotation_path=None,
        gene2go=None,
        background_genes=None,
        qvalue=0.05,
        methods=["bonferroni"],
        load_obsolete=False,
    ):
        """Load input files (allows to run GO enrichment analysis multiple times)."""
        self.obodag = GODag(obo_path, load_obsolete=load_obsolete, prt=None)

        if gene2go is None:
            gene2go, _ = read_emapper(annotation_path)

        if background_genes is None:
            background_genes = gene2go.keys()

        # Prepare GO enrichment
        self.qvalue = qvalue

        # Silently prepare GO enrichment analysis
        self.gostudy = GOEnrichmentStudy(
            background_genes, gene2go, self.obodag, methods=methods, alpha=self.qvalue, log=None
        )

    def run(self, query_genes, sort=False):
        """Calculate GO enrichment and semantic similarity."""

        # Run GO enrichment test (silently)
        results = self.gostudy.run_study(query_genes, prt=None)

        # Keep only significant terms
        results = [r for r in results if r.p_bonferroni <= self.qvalue]

        # Prune redundant GO terms
        reduced, semantic_dict = self.prune_go_terms(results, self.obodag)
        if len(reduced) == 0:
            return results

        # Append semantic similarity coordinates
        results = self.calculate_semantic_similarity_coords(reduced, semantic_dict)

        # Sort results based on adjusted p-value
        if sort:
            results = sorted(results, key=lambda x: x.get_pvalue())
        return results

    def calculate_semantic_similarity_coords(self, results, semantic_dict):
        """Calculate semantic similarity coordinates using MDS."""
        n = len(results)
        go_terms = [r.GO for r in results]

        # Create distance matrix
        dist_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            go_i = go_terms[i]
            for j in range(i + 1, n):
                go_j = go_terms[j]
                key = tuple(sorted((go_i, go_j)))
                dist = 1 - (semantic_dict.get(key) or 0)
                dist_matrix[i][j] = dist
                dist_matrix[j][i] = dist

        # Calculate semantic similarity coordinates using MDS
        semantic_mds = MDS(
            n_components=2,
            metric="precomputed",
            random_state=self.seed,
            init="classical_mds",
            n_init=1,
        ).fit_transform(dist_matrix)

        # Integrate coordinates into the results
        for i in range(len(results)):
            results[i].semantic_sim_coords = semantic_mds[i]

        return results

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

    def prune_go_terms(self, results, obodag, sim_cutoff=0.7, freq_cutoff=0.05, ci=0.1):
        """
        Prune GO terms using a REVIGO-like strategy.

        Calculates semantic similarity between all pairs of GO terms.

        Args:
            results (list): GO enrichment results.
            obodag (GODag): Full ontology parsed by GODag.
            sim_cutoff (float): Ignore GO semantic similarities below this threshold.
            freq_cutoff (float): Frequency threshold for removal.
            seed (int): Random seed to ensure consistent results.

        Returns:
            list[str]: Pruned GO IDs.
            dict[str, float]: Semantic similarity between GO term pairs.
        """
        # Random seed to ensure consistent results
        random.seed(self.seed)

        # Compute GO similarity matrix (upper triangle)
        n = len(results)
        discarded_gos = set()
        semantic_dict = {}

        for i in range(n):
            go_i = results[i]
            for j in range(i + 1, n):
                go_j = results[j]

                # Calculate and cache semantic similarity value
                key = tuple(sorted((go_i.GO, go_j.GO)))
                if key not in semantic_dict:
                    try:
                        semantic_dict[key] = semantic_similarity(go_i.GO, go_j.GO, obodag)
                    except ValueError:
                        semantic_dict[key] = 0
                    sim = semantic_dict[key]

                # Skip redundancy checks for this pair of GO terms
                if (
                    sim is None
                    or sim < sim_cutoff
                    or go_i.goterm.level <= 3
                    or go_j.goterm.level <= 3
                    or go_i in discarded_gos
                    or go_j in discarded_gos
                ):
                    continue

                # Remove GO terms according to REVIGO rules (Supek et al., 2011)
                is_go_i_freq = go_i.pop_count / go_i.pop_n > freq_cutoff
                is_go_j_freq = go_j.pop_count / go_j.pop_n > freq_cutoff

                go_i_abs_log_prop = abs(math.log10(max(go_i.p_bonferroni, 1e-300)))
                go_j_abs_log_prop = abs(math.log10(max(go_j.p_bonferroni, 1e-300)))
                go_sum_abs_log_prop = go_i_abs_log_prop + go_j_abs_log_prop
                relative_change = (
                    0
                    if go_sum_abs_log_prop == 0
                    else abs(go_i_abs_log_prop - go_j_abs_log_prop) / (go_sum_abs_log_prop / 2)
                )
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

                logger.debug(f"Discarded {discard.GO} for", reason)
                discarded_gos.add(discard)
                if go_i in discarded_gos:
                    break

        reduced = list(set(results) - discarded_gos) if discarded_gos else results
        return reduced, semantic_dict


class PfamEnrichmentRecord:
    """Result of Pfam domain enrichment for a single domain."""

    NS = "Pfam"

    def __init__(self, name, p_uncorrected, p_bonferroni, ratio_in_study, ratio_in_pop, study_items):
        """Store enrichment statistics for a Pfam domain."""
        self.term = name
        self.name = name
        self.p_uncorrected = p_uncorrected
        self.p_bonferroni = p_bonferroni
        self.ratio_in_study = ratio_in_study
        self.ratio_in_pop = ratio_in_pop
        self.study_items = study_items
        self.semantic_sim_coords = None

    @property
    def fold_enrichment(self):
        """Ratio of observed to expected representation (study proportion / population proportion)."""
        if self.ratio_in_study[1] == 0 or self.ratio_in_pop[1] == 0 or self.ratio_in_pop[0] == 0:
            return None
        return (1.0 * self.ratio_in_study[0] / self.ratio_in_study[1]) / (
            1.0 * self.ratio_in_pop[0] / self.ratio_in_pop[1]
        )

    def get_pvalue(self):
        """Return adjusted p-value (Bonferroni)."""
        return self.p_bonferroni

    def __repr__(self):
        """Representation."""
        return f"PfamEnrichmentRecord({self.term}, p={self.p_bonferroni})"


class PfamEnrichmentService:
    """Analyze Pfam domain enrichment."""

    def __init__(self, annotation_path=None, gene2pfam=None, background_genes=None, qvalue=0.05):
        """Load Pfam annotations (allows to run enrichment analysis multiple times)."""
        if gene2pfam is None:
            _, gene2pfam = read_emapper(annotation_path)
        self.gene2pfam = gene2pfam

        if background_genes is None:
            background_genes = list(gene2pfam)
        self.background_genes = list(background_genes)
        self.qvalue = qvalue

    def run(self, query_genes, sort=False):
        """Calculate Pfam domain enrichment."""
        query_genes = list(query_genes)
        study_n = len(query_genes)
        pop_n = len(self.background_genes)
        if study_n == 0 or pop_n == 0:
            return []

        # Count annotations in background and query
        pop_counts = Counter()
        for gene in self.background_genes:
            pop_counts.update(self.gene2pfam.get(gene, ()))

        study_counts = Counter()
        study_genes = {}
        for gene in query_genes:
            pfams = self.gene2pfam.get(gene, ())
            study_counts.update(pfams)
            for pfam in pfams:
                study_genes.setdefault(pfam, []).append(gene)

        # Apply Fisher's exact test per Pfam domain
        n_tests = len(study_counts)
        results = []
        for pfam, study_count in study_counts.items():
            study_hits = study_count
            pop_hits = pop_counts.get(pfam, 0)
            not_hits_study = study_n - study_hits
            not_hits_pop = pop_n - pop_hits - not_hits_study
            if pop_hits < study_hits or not_hits_pop < 0:
                continue

            # Use the same two-sided Fisher's exact test as GO enrichment (GOATOOLS)
            _, p_uncorrected = fisher_exact([[study_hits, not_hits_study], [pop_hits - study_hits, not_hits_pop]])
            p_bonferroni = min(p_uncorrected * n_tests, 1)
            if p_bonferroni <= self.qvalue:
                results.append(
                    PfamEnrichmentRecord(
                        name=pfam,
                        p_uncorrected=p_uncorrected,
                        p_bonferroni=p_bonferroni,
                        ratio_in_study=(study_hits, study_n),
                        ratio_in_pop=(pop_hits, pop_n),
                        study_items=study_genes[pfam],
                    )
                )

        # Sort results based on adjusted p-value
        if sort:
            results = sorted(results, key=lambda x: x.get_pvalue())
        return results
