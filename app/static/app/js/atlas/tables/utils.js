/* global $ */

import { getDataPortalUrl } from "../../utils/urls.js";

export function makeLinkGene(dataset) {
    return function linkGene(data, type) {
        if (type === "display") {
            let url = getDataPortalUrl("atlas_gene", dataset, data);
            if (url) {
                data = `<a href=${url}>${data}</a>`;
            }
        }
        return data;
    };
}

// Round numeric values
export function round(data, type) {
    if (type === "display" || type === "filter") {
        return parseFloat(data).toFixed(2);
    }
    return data;
}

// Improve array parsing
export function parseArray(data) {
    if (Array.isArray(data)) {
        return data.join(", ");
    }
    return data;
}

// Get selected rows
export function getSelectedRows(id) {
    return $(`#${id}`).DataTable().select.cumulative().rows.slice();
}
