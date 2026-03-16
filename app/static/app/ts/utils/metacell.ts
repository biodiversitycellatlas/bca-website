/**
 * Utility JavaScript functions for metacell selectize.
 */

function updateLabel(label, count) {
    const text = count > 0 ? "Selected metacells" : "All metacells";
    label.textContent = text;
}

/**
 * Update label based on number of selected metacells.
 */
export function initMetacellSelectionUpdater(label, select) {
    // Change label text
    const count = select.items.length;
    updateLabel(label, count);

    select.on("change", function () {
        const count = this.items.length;
        updateLabel(label, count);
    });
}
