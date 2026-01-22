/**
 * Plot gene expression comparisons.
 */

import $ from "jquery";

import { getDataPortalUrl } from "../utils/urls.ts";
import { updateDataMenu } from "../buttons/data_dropdown.ts";
import { createExpressionComparisonPlot } from "./plots/expression_plot.ts";
import { showSpinner, hideSpinner, clearContainer } from "./plots/plot_container.js";

/**
 * Plot expression comparison for the selected gene against a reference gene.
 *
 * @param {string} id - Table container ID.
 * @param {Object} dataset - Dataset reference.
 * @param {string} gene - Reference gene name for comparison.
 */
export function plotGeneExpressionComparison(id, dataset, gene) {
    $(`#${id}_table`)
        .DataTable()
        .on("select", function (e, dt, type) {
            if (type === "row") {
                let selected = dt.rows({ selected: true }).data();
                if (selected && selected.length > 0) {
                    let gene2 = selected[0].name;
                    loadExpressionComparison(
                        id,
                        dataset,
                        gene,
                        gene2,
                        selected[0],
                    );
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
