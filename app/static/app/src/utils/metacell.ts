/**
 * Utility JavaScript functions for metacell selectize.
 */

/**
 * Extract the trailing integer of a metacell name, used to order metacells.
 *
 * @param {string} name - Metacell name (e.g. "acrmil01_MC_00204" or "12").
 * @returns {number|null} Trailing integer, or null if the name has none.
 */
export function getMetacellIndex(name) {
    const match = String(name).match(/(\d+)$/);
    return match ? parseInt(match[1], 10) : null;
}

/**
 * Get the metacell order used to position metacells in heatmaps, falling back
 * to the trailing integer of the metacell name when no order is stored.
 *
 * @param {number|null} order - Stored metacell order (nullable).
 * @param {string} name - Metacell name (e.g. "acrmil01_MC_00204" or "12").
 * @returns {number|null} Metacell order or null if none is available.
 */
export function getMetacellOrder(order, name) {
    return order ?? getMetacellIndex(name);
}

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
