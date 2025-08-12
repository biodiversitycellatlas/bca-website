/**
 * Utility JavaScript functions to get URLs.
 */

/**
 * Prepare URL string with query parameters.
 *
 * @param {string} url - Base URL.
 * @param {string|null} dataset - Dataset identifier to add as query param (if not null).
 * @param {string|null} gene - Gene identifier to add as query param (if not null).
 * @param {number|null} limit - Limit value to add as query param (if not null).
 * @returns {string} The URL string with appended query parameters.
 */
function prepareUrlParams(url, dataset, gene, limit) {
    url = new URL(url, window.location.origin);
    if (dataset) url.searchParams.append('dataset', dataset);
    if (gene !== null) {
        if (Array.isArray(gene)) {
            url.searchParams.append('genes', gene[[0]]);
        } else {
            url.searchParams.append('gene', gene);
        }
    }
    if (limit !== null) url.searchParams.append('limit', limit);
    return url.toString();
}

/**
 * Generate URL for a given view, optionally including dataset, gene, and limit.
 *
 * For certain REST API views, query parameters are appended.
 * For other views, placeholders in the URL are replaced with provided values.
 *
 * @param {string} view - View key to look up the base URL.
 * @param {string|null} dataset - Dataset identifier.
 * @param {string|null} gene - Gene identifier.
 * @param {number|null} limit - Result limit.
 * @returns {string} Constructed URL.
 */
export function getDataPortalUrl(view, dataset=null, gene=null, limit=null) {
    let url = window.APP_URLS[view];
    if (!url) throw new Error(`URL for view "${view}" not found in APP_URLS.`);

    if ([
        "rest:metacellcount-list",
        "rest:correlated-list",
        "rest:singlecell-list",
        "rest:metacell-list",
        "rest:metacelllink-list",
    ].includes(view)) {
        url = prepareUrlParams(url, dataset, gene, limit);
    } else if (["rest:metacellgeneexpression-list"].includes(view)){
        url = prepareUrlParams(url, dataset, [gene], limit);
    } else {
        if (dataset) url = url.replace('DATASET_PLACEHOLDER', dataset);
        if (gene) url = url.replace('GENE_PLACEHOLDER', gene);
    }
    return url;
}
