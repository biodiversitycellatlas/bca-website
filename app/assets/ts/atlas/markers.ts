/**
 * Metacell markers page.
 */

import { getDataPortalUrl } from "../utils/urls.js";
import { createMarkersTable } from "../tables/markers_table.js";
import { convertToRange } from "../select/metacell.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";

/**
 * Toggle maximum fold-change slider based on selection.
 *
 * @param {HTMLSelectElement} elem - Select element controlling the slider.
 * @param {string} id - Selector for the ionRangeSlider element.
 */
export function toggleMaxFCslider(elem, id) {
    let slider = $(id).data("ionRangeSlider");
    if (elem.value == "ignore") {
        slider.update({ disable: true });
    } else {
        slider.update({ disable: false });
    }
}

/**
 * Simplify multiple select values into a comma-separated string
 * and update form submission.
 */
export function handleFormSubmit() {
    // Simplify multiple select data into a single comma-separated value
    $("form").on("submit", function (e) {
        e.preventDefault();

        // Get values
        let formData = new FormData(this);
        let values = formData.getAll("metacells").join(",");

        // Modify form URL
        let url = new URL(e.target.action);
        for (let [key, value] of formData.entries()) {
            url.searchParams.set(key, value);
        }
        url.searchParams.set("metacells", values);

        // Maintain commas in query params
        let href = url.href.replaceAll("%2C", ",");
        window.location.href = href;
    });
}

/**
 * Update the metacell selection label with a shortened, comma-separated label
 * and a tooltip showing full selection.
 *
 * Example: label shows "1-4, 7, 9-11" if selected = "1,2,3,4,7,9,10,11".
 *
 * @param {string} selected - Comma-separated list of selected metacells.
 */
export function updateMetacellSelectionLabel(selected) {
    let minimized = convertToRange(selected).replaceAll(",", ", ");
    let underline =
        'style="-webkit-text-decoration: underline dotted; text-decoration: underline dotted;"';
    let tooltip = `data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="${selected}"`;
    $("#selected_metacells").html(
        `<span ${underline} ${tooltip}>${minimized}</span>`,
    );
}

/**
 * Fetch marker data for selected metacells and create the markers table.
 *
 * @param {string} dataset - Dataset slug.
 * @param {string} metacells - Comma-separated list of selected metacells.
 * @param {string} fc_min_type - Type of minimum fold-change filtering.
 * @param {number} fc_min - Minimum fold-change value.
 * @param {string} fc_max_bg_type - Type of maximum background fold-change filtering.
 * @param {number} fc_max_bg - Maximum background fold-change value.
 */
export function initMarkersTable(
    dataset,
    metacells,
    fc_min_type,
    fc_min,
    fc_max_bg_type,
    fc_max_bg,
) {
    let url = getDataPortalUrl("rest:metacellmarker-list");
    let params = new URLSearchParams({
        dataset: dataset,
        metacells: metacells,
        fc_min_type: fc_min_type,
        fc_min: fc_min,
        fc_max_bg_type: fc_max_bg_type,
        fc_max_bg: fc_max_bg,
        limit: 0,
    });
    let apiURL = url + "?" + params.toString();

    createMarkersTable("markers", dataset, apiURL);
    appendDataMenu("markers", apiURL, "Metacell markers");
}
