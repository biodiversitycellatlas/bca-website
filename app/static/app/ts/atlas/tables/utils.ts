/**
 * Utility functions for DataTables displaying gene information.
 */

/* global $ */

import { getDataPortalUrl } from "../../utils/urls.ts";

/**
 * Factory function that returns a renderer linking gene names to the data portal.
 *
 * @param {Object} dataset - Dataset reference for constructing gene URLs.
 * @returns {Function} A render function for DataTables.
 */
export function makeLinkGene(dataset) {
    return function linkGene(data, type) {
        if (type === "display") {
            let url = getDataPortalUrl("atlas_gene", dataset, data);
            if (url) {
                data = `<a href=${url}>${data}</a>`;
            }
        }
        return data;
    };
}

/**
 * Round numeric values to two decimal places for display or filtering.
 *
 * @param {number|string} data - The numeric value to round.
 * @param {string} type - Rendering type: "display", "filter", etc.
 * @returns {string|number} Rounded value for display or original for other types.
 */
export function round(data, type) {
    if (type === "display" || type === "filter") {
        return parseFloat(data).toFixed(2);
    }
    return data;
}

/**
 * Convert an array into a comma-separated string for display.
 *
 * @param {Array|string} data - Array of values to join.
 * @returns {string} Comma-separated string or original value if not an array.
 */
export function parseArray(data) {
    if (Array.isArray(data)) {
        return data.join(", ");
    }
    return data;
}

/**
 * Get the currently selected rows from a DataTable.
 *
 * @param {string} id - HTML element ID of the DataTable.
 * @returns {Array} Array of selected row data.
 */
export function getSelectedRows(id) {
    return $(`#${id}`).DataTable().select.cumulative().rows.slice();
}
