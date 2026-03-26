/**
 * Utility JavaScript functions to get URLs.
 */

/**
 * Generate Data Portal URL for a given view.
 *
 * URL placeholders are replaced.
 *
 * @param {string} view - View key to look up the base URL.
 * @param {Object} [params={}] - Key-value pairs to append as query parameters.
 * @returns {string} Constructed URL.
 */
export function getDataPortalUrl(view, params = {}) {
    let url = window.APP_URLS[view];
    if (!url) throw new Error(`URL for view "${view}" not found in APP_URLS.`);

    // Replace placeholders with parameters
    url = url
        .replace("DATASET_PLACEHOLDER", params.dataset || "")
        .replace("GENE_PLACEHOLDER", params.gene || "")
        .replace("MODULE_PLACEHOLDER", params.gene_module || "")
        .replace("SPECIES_PLACEHOLDER", params.species || "")
        .replace("GENE_LIST_PLACEHOLDER", params.gene_list || "")
        .replace("ORTHOGROUP_PLACEHOLDER", params.orthogroup || "")
        .replace("DOMAIN_PLACEHOLDER", params.domain || "");

    // Replace consecutive slashes with a single slash
    url = url.replace(/\/+/g, "/");

    return url;
}

/**
 * Generate REST API URL for a given view.
 *
 * URL placeholders are replaced and query parameters are appended.
 *
 * @param {string} url - Base URL.
 * @param {Object} [params={}] - Key-value pairs to append as query parameters.
 * @returns {string} The URL string with appended query parameters.
 */
export function getRestUrl(view, params = {}) {
    let url = getDataPortalUrl(view, params);
    url = new URL(url, window.location.origin);

    // Append query parameters
    if (Object.keys(params).length > 0) {
        for (const key in params) {
            const value = params[key];
            if (value != null) url.searchParams.append(key, value);
        }
    }
    url = url.toString().replaceAll("%2C", ",");
    return url;
}
