/**
 * Module activity.
 */

import { getViewUrl } from "../utils/urls.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { createActivityHeatmap } from "./plots/metacell_heatmap.ts";

/**
 * Fetch module eigengenes for the given dataset and create a heatmap plot.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 */
export function loadEigengenes(id, dataset) {
    const url = getViewUrl("rest:genemoduleeigengene-list", {
        dataset,
        limit: 0,
        sort_modules: 1,
    });

    fetch(url)
        .then((response) => response.json())
        .then((data) => createActivityHeatmap(`#${id}-plot`, data))
        .catch((error) => console.error("Error fetching data:", error));

    appendDataMenu(id, url, "Eigengenes");
}
