/**
 * Utility JavaScript functions to get URLs.
 */

function prepareUrlParams(url, dataset, gene, limit) {
    var url = new URL(url, window.location.origin);
    if (dataset) url.searchParams.append('dataset', dataset);
    if (gene) url.searchParams.append('gene', gene);
    if (limit !== null) url.searchParams.append('limit', limit);
    return url.toString();
}

export function getDataPortalUrl(view, dataset=null, gene=null, limit=null) {
    let url = window.APP_URLS[view];

    if ([
        "rest:metacellcount-list",
        "rest:correlated-list",
        "rest:singlecell-list",
        "rest:metacell-list",
        "rest:metacelllink-list",
    ].includes(view)) {
        url = prepareUrlParams(url, dataset, gene, limit);
    } else {
        if (dataset) url = url.replace('DATASET_PLACEHOLDER', dataset);
        if (gene) url = url.replace('GENE_PLACEHOLDER', gene);
    }
    return url;
}
