/**
 * Utility JavaScript functions to get URLs.
 */

/**
 * Generate a URL for a given view.
 *
 * URL building:
 * - Define Base URLs in `app/templates/app/components/javascript_urls.html`.
 * - Provide parameters as key-value pairs: `{metacell: "17", species: "fox"}`.
 * - Matching placeholders (e.g. `METACELL_PLACEHOLDER`) are replaced with the
 *   corresponding values in the URL path.
 * - Remaining parameters are appended as query parameters (`?species=fox`).
 *
 * @param {string} view - View key to look up the base URL.
 * @param {Object} [params={}] - Key-value pairs as path and query parameters.
 * @returns {string} Constructed URL.
 */
export function getViewUrl(view, params = {}) {
    let url = window.APP_URLS[view];
    if (!url) throw new Error(`URL for view "${view}" not found in APP_URLS.`);

    // Find all placeholders
    const placeholders = url.match(/\b[A-Z0-9_]+_PLACEHOLDER\b/g) || [];

    // Replace placeholders with parameters (path parameters)
    for (const placeholder of placeholders) {
        const key = placeholder.replace("_PLACEHOLDER", "").toLowerCase();
        const value = params[key] ?? "";
        url = url.replace(placeholder, value);

        // Remove used parameter
        delete params[key];
    }

    // Fix consecutive slashes to ignore placeholders with no value
    url = url.replace(/\/+/g, "/");

    // Append remaining parameters as query parameters
    let finalUrl = new URL(url, window.location.origin);
    for (const key in params) {
        const value = params[key];
        if (value != null) finalUrl.searchParams.append(key, value);
    }

    // Replace with final URL
    finalUrl = finalUrl.pathname + finalUrl.search + finalUrl.hash;
    finalUrl = finalUrl.replaceAll("%2C", ",");
    return finalUrl;
}
