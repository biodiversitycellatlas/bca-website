/**
 * Module activity.
 */

import { getDataPortalUrl } from "../utils/urls.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { createSimilarityPlot } from "./plots/similarity_plot.ts";
import { hideSpinner } from "./plots/plot_container.ts";

/**
 * Handler factory for click events on similarity plot.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset1 - Dataset 1 slug to fetch expression data for.
 * @param {string} dataset1html - Dataset 1 HTML representation.
 * @param {string} dataset2 - Dataset 2 slug to fetch expression data for.
 * @param {string} dataset2html - Dataset 1 HTML representation.
 * @param {function} callback - Function to call with id, dataset and selected modules as arguments.
 */
export function createClickHandler(id, dataset1, dataset1html, dataset2, dataset2html, callback) {
    return function handleClick(event, item) {
        const modules = [item.datum.module, item.datum.module2];
        callback(id, dataset1, dataset1html, dataset2, dataset2html, modules);
    };
}

/**
 * Fetch module eigengenes for the given dataset and create a heatmap plot.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset1 - Slug for the first dataset.
 * @param {string} label1 - Label for the first dataset
 * @param {string} dataset1html - HTML linking to the first dataset.
 * @param {string} dataset2 - Slug for the second dataset.
 * @param {string} label2 - Label for the second dataset.
 * @param {string} dataset2html - HTML linking to the second dataset.
 * @param {function} onClick - Function to call when user selects two modules in the plot.
 */
export function loadModuleSimilarityPlot(
    id,
    dataset1,
    label1,
    dataset1html,
    dataset2 = null,
    label2 = null,
    dataset2html = null,
    onClick = null,
) {
    // Add cross-dataset comparison if dataset2 is not null
    const url = getDataPortalUrl(
        "rest:genemodulesimilarity-list",
        dataset1,
        null,
        0,
        { ...(dataset2 && { dataset2 }), sort_modules: 1 },
    );

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            const clickHandler = createClickHandler(id, dataset1, dataset1html, dataset2, dataset2html, onClick);
            createSimilarityPlot(`#${id}-plot`, data, label1, label2, clickHandler);

            // Automatically compare modules with highest similarity score
            const mostSimilar = data.reduce((a, b) => a.similarity > b.similarity ? a : b);
            onClick(id, dataset1, dataset1html, dataset2, dataset2html, [mostSimilar.module, mostSimilar.module2]);
        })
        .catch((error) => console.error("Error fetching data:", error))
        .finally(() => hideSpinner(id));

    appendDataMenu(id, url, "Similarity");
}
