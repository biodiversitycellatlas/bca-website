/**
 * Visualize single-gene expression data.
 */

import { getDataPortalUrl } from "../utils/urls.ts";
import { hideSpinner } from "./plots/plot_container.ts";
import { createExpressionBubblePlot } from "./plots/expression_plot.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";

/**
 * Load gene expression data and create plot.
 *
 * @param {string} dataset - Dataset slug.
 * @param {string} datasetLabel - Dataset label.
 * @param {string} gene - Gene identifier used for the plot container ID.
 * @param {string} geneLabel - Gene name.
 */
export function loadGeneExpression(dataset, datasetLabel, gene, geneLabel) {
    let url = getDataPortalUrl(
        "rest:metacellgeneexpression-list",
        dataset,
        geneLabel,
        0,
    );
    appendDataMenu("expression", url, "gene expression");

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            if (data.length === 0) {
                document.getElementById(`${gene}-plot`).innerHTML =
                    `<p class='text-muted'><i class='fa fa-circle-exclamation'></i> No <b>${geneLabel}</b> expression for <i>${datasetLabel}</i>.</p>`;
            } else {
                createExpressionBubblePlot(`#${gene}-plot`, geneLabel, data);
            }
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        })
        .finally(() => {
            hideSpinner(gene);
        });
}
