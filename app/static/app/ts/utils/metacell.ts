/**
 * Utility JavaScript functions for metacell selectize.
 */

function updateLabel(select, count) {
    const label = count > 0 ? "Selected metacells" : "All metacells";
    select.text(label);
}

/**
 * Update label based on number of selected metacells.
 */
export function initMetacellSelectionUpdater(select) {
    // Change select label
    const count = select.items.length;
    updateLabel(select, count);

    select.on("change", function () {
        const count = this.items.length;
        updateLabel(select, count);
    });
}
