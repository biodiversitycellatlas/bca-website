/**
 * Gene panel expression page.
 */

import $ from "jquery";

import { getDataPortalUrl } from "../utils/urls.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { createExpressionHeatmap } from "./plots/expression_heatmap.ts";
import { getUserLists } from "./modals/list_editor.ts";

/**
 * Fetch expression data for the given dataset and optional gene list,
 * then create a heatmap plot and update the data menu.
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {string|null} genes - Optional comma-separated list of gene names to include.
 */
export function loadExpressionData(id, dataset, genes = null) {
    const url = getDataPortalUrl("rest:metacellgeneexpression-list");

    const params = new URLSearchParams({
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

    const apiURL = url + "?" + params.toString();

    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            createExpressionHeatmap(`#${id}-plot`, dataset, data);
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
    const formData = new FormData(elem);
    const url = new URL(e.target.action);
    for (const [key, value] of formData.entries()) {
        url.searchParams.set(key, value);
    }

    // Get values
    for (const i in multiple) {
        const param = multiple[i];
        const values = formData.getAll(param);
        url.searchParams.set(param, values.join(","));

        // Process values from user lists as hidden query parameters
        if (param == "gene_lists") {
            // Get genes from user lists
            const lists = getUserLists(`${id}_${param}`, dataset);
            const matches = lists.filter((list) => values.includes(list.name));
            let genes = matches.flatMap((list) => list.items);

            // Get remaining lists
            const names = matches.flatMap((list) => list.name);
            const diff = values.filter((value) => !names.includes(value));
            genes = diff.concat(genes);

            // Set query parameter
            url.searchParams.set("genes", genes.join(","));
        }
    }

    // Maintain commas in query params
    const href = url.href.replaceAll("%2C", ",");
    window.location.href = href;
}

/**
 * When submitting form, modify query params for multiple selects.
 *
 * @param {string} type - Form type, e.g. "gene-lists" to enable extra processing.
 */
export function handleFormSubmit(id, dataset, type) {
    $("form").on("submit", function (e) {
        const multiple = ["metacell_lists"];
        if (type === "gene-lists") multiple.push("gene_lists");
        modifyFormQuery(this, e, id, dataset, multiple);
    });
}

function toggleSubmitButton(id) {
    const elem = $(`#${id}_gene_selection`)[0].selectize;
    const isEmpty = elem.items.length === 0;
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

function updateMetacellSelectionLabel(count) {
    const label = count > 0 ? "Selected metacells" : "All metacells";
    $("#metacells_filter").text(label);
}

/**
 * Update label based on number of selected metacells.
 */
export function initMetacellSelectionLabelUpdater() {
    // Change metacell selection label
    const metacell_selectize = $("#metacells")[0].selectize;
    const count = metacell_selectize.items.length;
    updateMetacellSelectionLabel(count);

    metacell_selectize.on("change", function () {
        const count = this.items.length;
        updateMetacellSelectionLabel(count);
    });
}
