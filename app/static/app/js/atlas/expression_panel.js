/**
 * Gene panel expression page.
 */

/* global $ */

import { getDataPortalUrl } from "../utils/urls.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";
import { createExpressionHeatmap } from "../plots/metacell_heatmap.js";
import { getUserLists } from "./modals/list_editor.js";

/**
 * Fetch expression data for the given dataset and optional gene list,
 * then create a heatmap plot and update the data menu.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {string|null} genes - Optional comma-separated list of gene names to include.
 */
export function loadExpressionData(id, dataset, genes = null) {
    let url = getDataPortalUrl("rest:metacellgeneexpression-list");

    let params = new URLSearchParams({
        dataset: dataset,
        metacells: $("#metacells").val().join(","),
        fc_min: $("#fc_min").val(),
        sort_genes: true,
        log2: true,
        clip_log2: $("#clip_log2").val(),
        limit: 0,
    });

    if (genes) {
        params.append("genes", genes);
    } else {
        params.append("n_markers", $("#markers").val());
    }

    let apiURL = url + "?" + params.toString();

    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            createExpressionHeatmap(`#${id}-plot`, data);
        })
        .catch((error) => console.error("Error fetching data:", error));

    appendDataMenu(id, apiURL, "Metacell gene expression");
}

/**
 * Modify form submission URL by converting multiple select fields into comma-separated query params,
 * and processing gene list selections into a consolidated 'genes' parameter.
 *
 * @param {HTMLFormElement} elem - The form element being submitted.
 * @param {Event} e - The submit event.
 * @param {string} id - Identifier used to fetch user gene lists.
 * @param {string} dataset - Dataset slug for user list retrieval.
 * @param {Array<string>} multiple - Array of form field names that can have multiple selected values.
 */
function modifyFormQuery(elem, e, id, dataset, multiple = []) {
    e.preventDefault();

    // Modify form URL
    let formData = new FormData(elem);
    let url = new URL(e.target.action);
    for (let [key, value] of formData.entries()) {
        url.searchParams.set(key, value);
    }

    // Get values
    for (let i in multiple) {
        let param = multiple[i];
        let values = formData.getAll(param);
        url.searchParams.set(param, values.join(","));

        // Process values from user lists as hidden query parameters
        if (param == "gene_lists") {
            // Get genes from user lists
            let lists = getUserLists(`${id}_${param}`, dataset);
            let matches = lists.filter((list) => values.includes(list.name));
            let genes = matches.flatMap((list) => list.items);

            // Get remaining lists
            let names = matches.flatMap((list) => list.name);
            let diff = values.filter((value) => !names.includes(value));
            genes = diff.concat(genes);

            // Set query parameter
            url.searchParams.set("genes", genes.join(","));
        }
    }

    // Maintain commas in query params
    let href = url.href.replaceAll("%2C", ",");
    window.location.href = href;
}

/**
 * When submitting form, modify query params for multiple selects.
 *
 * @param {string} type - Form type, e.g. "gene-lists" to enable extra processing.
 */
export function handleFormSubmit(id, dataset, type) {
    $("form").on("submit", function (e) {
        let multiple = ["metacell_lists"];
        if (type === "gene-lists") multiple.push("gene_lists");
        modifyFormQuery(this, e, id, dataset, multiple);
    });
}

function toggleSubmitButton(id) {
    let elem = $(`#${id}_gene_selection`)[0].selectize;
    let isEmpty = elem.items.length === 0;
    $(`#${id}_submit`).prop("disabled", isEmpty);
}

/**
 * Toggle the gene selection submit button based on current selection.
 *
 * @param {string} id - Element identifier.
 */
export function initSubmitButtonToggler(id) {
    // Enable/disable submit button
    toggleSubmitButton(id);
    $("#expression_gene_selection")[0].selectize.on("change", function () {
        toggleSubmitButton(id);
    });
}
