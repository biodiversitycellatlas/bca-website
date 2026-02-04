/**
 * Gene correlation table and plot functions.
 */

import "datatables.net-bs5";
import "datatables.net-select-bs5";

import { getDataPortalUrl } from "../utils/urls.ts";
import { appendDataMenu, updateDataMenu } from "../buttons/data_dropdown.ts";
import { createGeneTable } from "./tables/gene_table.ts";
import { createExpressionComparisonPlot } from "./plots/expression_plot.ts";
import {
    showSpinner,
    hideSpinner,
    clearContainer,
} from "./plots/plot_container.js";

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
function createGeneCorrelationTable(id, dataset, gene) {
    // Get lists from API
    const corrURL = getDataPortalUrl("rest:correlated-list", dataset, gene);
    appendDataMenu(id, corrURL, "Correlation table (current page)");
    const table = createGeneTable(
        `${id}_table`,
        dataset,
        corrURL,
        true,
        "single",
    );
    return table;
}

/**
 * Plot expression comparison for the selected gene against a reference gene.
 *
 * @param {string} jQuery - Table element.
 * @param {string} id - Table container ID.
 * @param {Object} dataset - Dataset reference.
 * @param {string} gene - Reference gene name for comparison.
 */
function plotGeneExpressionComparison(table, id, dataset, gene) {
    table.on("select", function (e, dt, type) {
        if (type === "row") {
            const selected = dt.rows({ selected: true }).data();
            if (selected && selected.length > 0) {
                const gene2 = selected[0].name;
                loadExpressionComparison(id, dataset, gene, gene2, selected[0]);
            }
        }
    });

    // Hide spinner if gene correlation table is empty
    hideSpinner(id);
}

/**
 * Fetch expression data for two genes and render a comparison plot.
 *
 * @param {string} id - Plot container ID.
 * @param {Object} dataset - Dataset reference.
 * @param {string} gene - First gene.
 * @param {string} gene2 - Second gene (selected gene).
 * @param {Object} stats - Metadata or statistics for the selected gene.
 */
function loadExpressionComparison(id, dataset, gene, gene2, stats) {
    // Create URL to fetch expression data for both genes
    let apiURL = getDataPortalUrl(
        "rest:metacellgeneexpression-list",
        dataset,
        `${gene},${gene2}`,
        0,
    );
    apiURL = apiURL.replaceAll("%2C", ",");
    updateDataMenu(id, apiURL, "Expression comparison (plot data)");

    // Fetch data from the API and create plot
    clearContainer(id);
    showSpinner(id);
    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            createExpressionComparisonPlot(
                `#${id}-plot`,
                gene,
                gene2,
                data,
                stats,
            );
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        })
        .finally(() => {
            hideSpinner(id);
        });
}

/**
 * Load gene correlation interface.
 *
 * @param {string} id - Container element ID for the table.
 * @param {Object} dataset - Dataset reference for linking genes and fetching data.
 * @param {string} gene - Gene ID for which to load correlated genes.
 */
export function loadGeneCorrelation(id, dataset, gene) {
    // Create gene correlation table
    const table = createGeneCorrelationTable(id, dataset, gene);

    // Plot expression data to compare two genes based on table selection
    plotGeneExpressionComparison(table, id, dataset, gene);
}
