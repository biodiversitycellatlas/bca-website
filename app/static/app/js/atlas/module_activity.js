/**
 * Module activity.
 */

import { getDataPortalUrl } from "../utils/urls.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";
import { createActivityHeatmap } from "../plots/metacell_heatmap.js";

/**
 * Fetch eigenvalues for the given dataset and create a heatmap plot.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 */
export function loadEigenvalues(id, dataset) {
    let url = getDataPortalUrl(
        "rest:genemoduleeigenvalue-list",
        dataset,
        null,
        0,
        { sort_modules: 1 },
    );

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            createActivityHeatmap(`#${id}-plot`, data);
        })
        .catch((error) => console.error("Error fetching data:", error));

    appendDataMenu(id, url, "Eigenvalues");
}
