/* global $ */

import { getDataPortalUrl } from "../utils/urls.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";
import { hideSpinner } from "../plots/plot_container.js";
import { createSAMapSankey } from "../plots/samap_sankey_plot.js";

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
    var formData = new FormData(elem);
    var url = new URL(e.target.action);
    for (let [key, value] of formData.entries()) {
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

export function loadSAMapData(id, label, dataset, label2, dataset2) {
    var params = new URLSearchParams({
        dataset: dataset,
        dataset2: dataset2,
        threshold: $("#samap_min").val(),
        limit: 0,
    });
    var apiURL = getDataPortalUrl("rest:samap-list") + "?" + params.toString();

    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            if (data.length) {
                createSAMapSankey(`#${id}-plot`, data, label, label2);
            } else {
                $(`#${id}-plot`).html(
                    '<p class="text-muted"><i class="fa fa-circle-exclamation"></i>',
                    "No data available for the selected datasets.</p>",
                );
            }
        })
        .catch((error) => console.error("Error fetching data:", error))
        .finally(() => {
            hideSpinner(id);
        });

    appendDataMenu(id, apiURL, "SAMap scores");
}
