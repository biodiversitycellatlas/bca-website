/**
 * Utility functions for DataTables displaying gene information.
 */

import $ from "jquery";
import "datatables.net-bs5";
import "datatables.net-select-bs5";

import { getDataPortalUrl } from "../../utils/urls.ts";

/**
 * Creates an HTML anchor element as a string.
 *
 * @param {string} text - The text to display for the link.
 * @param {string} url - The URL the link should point to.
 * @returns {string} HTML string of the anchor element.
 */
function linkElement(text, url) {
    const a = document.createElement("a");
    a.href = url;
    a.textContent = text;
    return a.outerHTML;
}

/**
 * Factory function that returns a renderer linking gene names to the data portal.
 *
 * @param {Object} dataset - Dataset reference for constructing gene URLs.
 * @returns {Function} A render function for DataTables.
 */
export function makeLinkGene(dataset) {
    return function linkGene(data, type) {
        if (type === "display") {
            const url = getDataPortalUrl("atlas_gene", dataset, data);
            if (url) linkElement(data, url);
        }
        return data;
    };
}

/**
 * Converts an array of domain names into HTML links pointing to the data portal.
 *
 * @param {Array<string>} domains - Array of domain names to link.
 * @param {string} type - The DataTables rendering type (e.g., "display").
 * @returns {string|Array<string>} Comma-separated HTML links if type is "display"; otherwise, returns the original domains array.
 */
export function linkDomains(domains, type) {
    const domainLinks = [];
    if (type === "display") {
        for (const domain of domains) {
            const url = getDataPortalUrl("domain_entry", null, null, null, {
                domain,
            });
            if (url) domainLinks.push(linkElement(domain, url));
        }
    }
    return domainLinks.length ? domainLinks.join(", ") : domains;
}

/**
 * Converts an orthogroup identifier into an HTML link pointing to the data portal.
 *
 * @param {string} orthogroup - The orthogroup identifier.
 * @param {string} type - The DataTables rendering type (e.g., "display").
 * @returns {string} HTML link if type is "display"; otherwise, returns the original orthogroup string.
 */
export function linkOrthogroup(orthogroup, type) {
    if (type === "display") {
        const url = getDataPortalUrl("orthogroup_entry", null, null, null, {
            orthogroup,
        });
        if (url) orthogroup = linkElement(orthogroup, url);
    }
    return orthogroup;
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
