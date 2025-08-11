/**
 * Utility JavaScript functions.
 */

function prepareUrlParams(url, dataset) {
    var url = new URL(url, window.location.origin);
    url.searchParams.append('dataset', dataset);
    url.searchParams.append('limit', '0');
    return url.toString();
}

export function getDataPortalUrl(view, dataset=null, gene=null) {
    let url = window.APP_URLS[view];

    if (view === "rest:metacellcount-list") {
        url = prepareUrlParams(url, dataset);
    } else {
        if (dataset) url = url.replace('DATASET_PLACEHOLDER', dataset);
        if (gene) url = url.replace('GENE_PLACEHOLDER', gene);
    }
    return url;
}
