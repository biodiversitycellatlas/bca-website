/**
 * Visualize SAMap comparisons between datasets.
 */

import $ from "jquery";

import { getViewUrl } from "../utils/urls.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { hideSpinner } from "./plots/plot_container.ts";
import { createSAMapSankey } from "./plots/samap_sankey_plot.ts";
import { createSAMapHeatmap } from "./plots/samap_heatmap.js";

/**
 * Update parameter and reload page.
 *
 * @param {string} param - Parameter name to set.
 * @param {string} value - Value.
 */
export function updateParam(param, value) {
    const url = new URL(window.location);
    url.searchParams.set(param, value);
    window.location.href = url.href;
}

/**
 * Navigate to new URL query parameters based on form data.
 * Maintains query when changing only one value.
 *
 * @param {HTMLFormElement} elem - The form element being submitted.
 * @param {Event} e - The submit event.
 */
function modifyFormQuery(elem, e) {
    e.preventDefault();

    // Modify form URL
    const formData = new FormData(elem);
    const url = new URL(e.target.action);
    for (const [key, value] of formData.entries()) {
        url.searchParams.set(key, value);
    }
    window.location.href = url.href;
}

/**
 * When submitting form, modify query params.
 */
export function handleFormSubmit() {
    $("form").on("submit", function (e) {
        modifyFormQuery(this, e);
    });
}

/**
 * Fetch and display metacell type similarity between datasets.
 * Renders a Sankey plot showing cell-type correspondences.
 *
 * @param {string} id - HTML element ID prefix for the plot container
 * @param {string} label - Label for the first dataset
 * @param {string} dataset - Name of the first dataset
 * @param {string} label2 - Label for the second dataset
 * @param {string} dataset2 - Name of the second dataset
 */
export function initSAMap(id, label, dataset, label2, dataset2) {
    const url = getViewUrl("rest:metacelltypesimilarity-list", {
        dataset,
        dataset2,
        min_samap: $("#min_samap").val(),
        limit: 0,
    });

    const heatmap = $("#plot").val() == "heatmap";
    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            if (!data.length) {
                const plot = document.getElementById(`${id}-plot`);
                plot.parentElement.parentElement.innerHTML = `
                    <p class="text-muted">
                        <i class="fa fa-circle-exclamation"></i>
                        No data available for the selected datasets.
                    </p>
                `;
            } else if (heatmap) {
                createSAMapHeatmap(`#${id}-plot`, data, label, label2);
            } else {
                createSAMapSankey(`#${id}-plot`, data, label, label2);
            }
        })
        .catch((error) => console.error("Error fetching data:", error))
        .finally(() => hideSpinner(id));

    appendDataMenu(id, url, "SAMap scores");
}
