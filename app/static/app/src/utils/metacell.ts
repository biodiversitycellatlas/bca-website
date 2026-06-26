/**
 * Utility JavaScript functions for metacell selectize.
 */

function updateLabel(element, count) {
    const label = count > 0 ? "Selected metacells" : "All metacells";
    element.textContent = label;
}

/**
 * Update label based on number of selected metacells.
 */
export function initMetacellSelectionUpdater(select, element) {
    // Change select label
    const count = select.items.length;
    updateLabel(element, count);

    select.on("change", function () {
        const count = this.items.length;
        updateLabel(element, count);
    });
}
