import { getDataPortalUrl } from "../utils/urls.js";
import { createExpressionComparisonPlot } from "./plots/expression_plot.js";
import { updateDataMenu } from "../buttons/data_dropdown.js";

/* global $ */

export function plotGeneExpressionComparison(id, dataset, gene) {
    $(`#${id}_table`)
        .DataTable()
        .on("select", function (e, dt, type, indexes) {
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
