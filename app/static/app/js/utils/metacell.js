/**
 * Utility JavaScript functions for metacell selectize.
 */

/* global $ */

function updateLabel(id, count) {
    let label = count > 0 ? "Selected metacells" : "All metacells";
    $(id).text(label);
}

/**
 * Update label based on number of selected metacells.
 */
export function initMetacellSelectionUpdater() {
    // Change metacell selection label
    const metacell_selectize = $("#metacells")[0].selectize;
    let count = metacell_selectize.items.length;
    updateLabel("#metacells_filter", count);

    metacell_selectize.on("change", function () {
        let count = this.items.length;
        updateLabel("#metacells_filter", count);
    });
}
