import { getDataPortalUrl } from "../utils/urls.js";
import { createExpressionBubblePlot } from "./plots/expression_plot.js";

// Create URL to fetch gene expression data
export function loadGeneExpression(dataset, datasetLabel, gene, geneLabel) {
    let url = getDataPortalUrl("rest:metacellgeneexpression-list", dataset, geneLabel, 0);
    appendDataMenu("expression", url, "gene expression");

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                document.getElementById(`${gene}-plot`).innerHTML = `<p class='text-muted'><i class='fa fa-circle-exclamation'></i> No <b>${geneLabel}</b> expression for <i>${datasetLabel}</i>.</p>`
            } else {
                createExpressionBubblePlot(`#${gene}-plot`, geneLabel, data);
            }
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        })
        .finally(() => {
            hideSpinner(gene);
        });
}
