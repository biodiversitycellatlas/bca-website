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

/**
 * Compute a stable heatmap position for each metacell, using the stored order
 * or falling back to the trailing integer of the name. When the fallback is
 * disabled (e.g. module activity), metacells keep their position in the data.
 *
 * @param {Array} data - Heatmap records containing metacell_name and metacell_order.
 * @param {boolean} [fallbackMetacellIndex=true] - Fall back to the trailing number of the metacell name.
 * @returns {Map<string, number|null>} Map of metacell name to position.
 */
export function getMetacellPositions(data, fallbackMetacellIndex = true) {
    const positions = new Map();
    data.forEach((obj, i) => {
        if (!positions.has(obj.metacell_name)) {
            positions.set(
                obj.metacell_name,
                obj.metacell_order ?? (fallbackMetacellIndex ? getMetacellIndex(obj.metacell_name) : i),
            );
        }
    });
    return positions;
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
