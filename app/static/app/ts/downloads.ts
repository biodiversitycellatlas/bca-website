/**
 * Download page functions.
 */

import $ from "jquery";
import "datatables.net-bs5";
import "datatables.net-select-bs5";

/**
 * Render DataTables for downloading data.
 *
 * @param {Object} obj - Hierarchical tree object
 * @returns {Array} Flattened array with nodes containing id, parent, name, and size
 */
export function renderTables(id) {
    $(id).DataTable({
        responsive: true,
        pageLength: 25,
        scrollX: true,
        language: { "search": "" }
    });

    $(".dt-search input").attr("placeholder", "Search table...");
}
