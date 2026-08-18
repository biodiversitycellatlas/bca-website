/**
 * Shared utilities for tables and DataTables.
 */

/**
 * Convert DataTables request parameters to DRF-compatible query params.
 *
 * @param {Object} data - DataTables request parameters.
 * @param {Array<Object>} data.order - Column ordering specifications.
 * @param {number} data.start - Offset for pagination.
 * @param {number} data.length - Limit for pagination.
 * @param {Object} data.search - Search object with a value property.
 * @returns {Object} Params object with offset, limit, q, and ordering keys.
 */
export function buildDataQuery(data, species, genes, method = "GET") {
    let ordering;
    if (data.order && data.order[0]) {
        const o = data.order[0];
        ordering = (o.dir == "desc" ? "-" : "") + o.name;
    }

    const params = {
        offset: data.start,
        limit: data.length,
        q: data.search.value,
        ordering: ordering,
    };
    if (typeof species === "string") params.species = species;
    if (Array.isArray(genes)) params.genes = genes;
    return method === "POST" ? JSON.stringify(params) : params;
}

/**
 * Transform DRF paginated JSON into DataTables-compatible format.
 *
 * Maps DRF's `count` to `recordsTotal`/`recordsFiltered` and leaves
 * `dataSrc` responsible for extracting the results array.
 *
 * @param {string} data - Raw JSON string from the API response.
 * @returns {string} Modified JSON string with DataTables metadata fields.
 */
export function filterData(data) {
    const json = JSON.parse(data);
    json.recordsTotal = json.count;
    json.recordsFiltered = json.count;
    json.data = json.list;
    return JSON.stringify(json);
}
