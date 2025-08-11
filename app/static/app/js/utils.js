/**
 * Utility JavaScript functions.
 */

export function getDataPortalUrl(view, dataset=null, gene=null) {
    let url = window.urls[view];
    if (dataset) url = url.replace('DATASET_PLACEHOLDER', dataset);
    if (gene) url = url.replace('GENE_PLACEHOLDER', gene);
    return url;
}
