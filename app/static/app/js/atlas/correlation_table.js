/**
 * Gene correlation table functions.
 */

import { getDataPortalUrl } from "../utils/urls.js";
import { createGeneTable } from "./tables/gene_table.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";

/**
 * Load a gene correlation table for a given gene.
 *
 * Fetches correlated gene data from the API, adds a data menu, and
 * initializes a single-selection gene DataTable with correlation columns.
 *
 * @param {string} id - Container element ID for the table.
 * @param {Object} dataset - Dataset reference for linking genes and fetching data.
 * @param {string} gene - Gene ID for which to load correlated genes.
 */
export function loadGeneCorrelationTable(id, dataset, gene) {
    // Get lists from API
    var corrURL = getDataPortalUrl("rest:correlated-list", dataset, gene);
    appendDataMenu(id, corrURL, "Correlation table (current page)");
    createGeneTable(`${id}_table`, dataset, corrURL, true, "single");
}
