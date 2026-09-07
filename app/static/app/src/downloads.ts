/**
 * Download page functions.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-select-bs5";

/**
 * Render DataTables for downloading data.
 *
 * @param {string} selectors - Comma-separated table selectors to initialize.
 */
export function renderTables(selectors) {
    const tables = [];
    for (const selector of selectors.split(",")) {
        const id = selector.trim();
        const table = new DataTable(id, {
            pageLength: 25,
            scrollX: true,
            language: { search: "", searchPlaceholder: "Search table..." },
        });
        tables.push(table);
    }
    return tables;
}
