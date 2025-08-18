/* global $ */

import { getDataPortalUrl } from "../utils/urls.js";
import { createMarkersTable } from "./tables/markers_table.js";
import { convertToRange } from "../select/metacell.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";

export function toggleMaxFCslider(elem, id) {
    let slider = $(id).data("ionRangeSlider");
    if (elem.value == "ignore") {
        slider.update({ disable: true });
    } else {
        slider.update({ disable: false });
    }
}

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

export function updateMetacellSelectionLabel(selected) {
    let minimized = convertToRange(selected).replaceAll(",", ", ");
    let underline =
        'style="-webkit-text-decoration: underline dotted; text-decoration: underline dotted;"';
    let tooltip = `data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="${selected}"`;
    $("#selected_metacells").html(
        `<span ${underline} ${tooltip}>${minimized}</span>`,
    );
}

export function loadMarkersData(
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
