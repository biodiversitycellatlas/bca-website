import { getDataPortalUrl } from "../utils.js";
import { createExpressionHeatmap } from "./plots/expression_heatmap.js";

export function loadExpressionData(id, dataset, genes=null) {
    var url = getDataPortalUrl("rest:metacellgeneexpression-list");

    var params = new URLSearchParams({
        dataset: dataset,
        metacells: $("#metacells").val().join(","),
        fc_min: $("#fc_min").val(),
        sort_genes: true,
        log2: true,
        clip_log2: $("#clip_log2").val(),
        limit: 0
    });

    if (genes) {
        params.append("genes", genes);
    } else {
        params.append("n_markers", $("#markers").val());
    }

    var apiURL = url + "?" + params.toString();

    fetch(apiURL)
        .then(response => response.json())
        .then(data => {
            createExpressionHeatmap(`#${id}-plot`, dataset, data)
        })
        .catch(error => console.error('Error fetching data:', error));

    appendDataMenu(id, apiURL, 'Metacell gene expression');
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
function modifyFormQuery (elem, e, id, dataset, multiple = []) {
    e.preventDefault();

    // Modify form URL
    var formData = new FormData(elem);
    var url = new URL(e.target.action);
    for (let [key, value] of formData.entries()) {
        url.searchParams.set(key, value);
    }

    // Get values
    for (var i in multiple) {
        var param = multiple[i];
        var values = formData.getAll(param);
        url.searchParams.set(param, values.join(','));

        // Process values from user lists as hidden query parameters
        if (param == 'gene_lists') {
            // Get genes from user lists
            var lists = getUserLists(`${id}_${param}`, dataset);
            let matches = lists.filter(list => values.includes(list.name));
            var genes = matches.flatMap(list => list.items);

            // Get remaining lists
            var names = matches.flatMap(list => list.name);
            var diff = values.filter(value => !names.includes(value));
            genes = diff.concat(genes);

            // Set query parameter
            url.searchParams.set('genes', genes.join(','));
        }
    }

    // Maintain commas in query params
    let href = url.href.replaceAll('%2C', ',');
    window.location.href = href;
}

/**
 * When submitting form, modify query params for multiple selects.
 *
 * @param {string} type - Form type, e.g. "gene-lists" to enable extra processing.
 */
export function handleFormSubmit(type) {
    $('form').on('submit', function(e) {
        var multiple = ['metacell_lists'];
        if (type === "gene-lists") multiple.push('gene_lists');
        modifyFormQuery(this, e, '{{id}}', '{{dataset.slug}}', multiple);
    });
}

function updateText(id, from_min_id, suffix="") {
    return function update(data) {
        $(id).text(data.from + suffix);

        // Update from_min of given ionRangeSlider
        if (from_min_id && from_min_id !== null) {
            $(from_min_id).data("ionRangeSlider").update({from_min: data.from})
        }
    }
}

export function initRangeSlider(selector, opts, textArgs) {
    const baseOpts = { grid: true, skin: "round" };
    const cb = updateText(...textArgs);
    $(selector).ionRangeSlider({
        ...baseOpts,
        ...opts,
        onStart: cb,
        onChange: cb,
        onUpdate: cb
    });
}

function toggleSubmitButton(id) {
    var elem = $(`#${id}_gene_selection`)[0].selectize;
    var isEmpty = elem.items.length === 0;
    $(`#${id}_submit`).prop('disabled', isEmpty);
}

export function initSubmitButtonToggler(id) {
    // Enable/disable submit button
    toggleSubmitButton(id);
    $('#expression_gene_selection')[0].selectize.on('change', function() {
        toggleSubmitButton(id);
    });
}

function updateMetacellSelectionLabel (count) {
    var label = count > 0 ? 'Selected metacells' : 'All metacells';
    $('#metacells_filter').text(label);
}

export function initMetacellSelectionLabelUpdater() {
    // Change metacell selection label
    const metacell_selectize = $('#metacells')[0].selectize;
    var count = metacell_selectize.items.length;
    updateMetacellSelectionLabel(count);

    metacell_selectize.on('change', function() {
        var count = this.items.length;
        updateMetacellSelectionLabel(count);
    });
}

