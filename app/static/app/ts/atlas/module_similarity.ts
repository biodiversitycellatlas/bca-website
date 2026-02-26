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
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {function} callback - Function to call with id, dataset and selected modules as arguments.
 */
export function createClickHandler(id, dataset, callback) {
    return function handleClick(event, item) {
        const modules = [item.datum.module, item.datum.module2];
        callback(id, dataset, modules);
    };
}

/**
 * Fetch module eigengenes for the given dataset and create a heatmap plot.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {function} onClick - Function to call when user selects two modules in the plot.
 */
export function loadModuleSimilarityPlot(id, dataset, onClick = null) {
    const url = getDataPortalUrl(
        "rest:genemodulesimilarity-list",
        dataset,
        null,
        0,
    );

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            const clickHandler = createClickHandler(id, dataset, onClick);
            createSimilarityPlot(`#${id}-plot`, data, clickHandler);

            // Automatically compare modules with highest similarity score
            const mostSimilar = data.reduce((a, b) =>
                a.similarity > b.similarity ? a : b,
            );
            onClick(id, dataset, [mostSimilar.module, mostSimilar.module2]);
        })
        .catch((error) => console.error("Error fetching data:", error))
        .finally(() => hideSpinner(id));

    appendDataMenu(id, url, "Similarity");
}
