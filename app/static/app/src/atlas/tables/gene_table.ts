/**
 * Create interactive gene tables using DataTables.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-select-bs5";

import { buildDataQuery, filterData } from "../plots/utils.ts";
import { makeLinkGene, linkDomains } from "./utils.ts";

/**
 * Initialize a DataTable for displaying gene information.
 * Supports optional correlation columns and selection modes.
 *
 * @param {string} id - Table element ID.
 * @param {Object} dataset - Dataset reference used for linking genes.
 * @param {string} species - Species slug.
 * @param {string} url - Data source URL for AJAX loading.
 * @param {Object} [options]
 * @param {boolean} [options.correlation=false] - Whether to include correlation columns.
 * @param {string} [options.select="none"] - Selection mode: "multiple", "single", or "none".
 * @param {Array[string]} [options.genes=null] - Array of genes to send to POST.
 */
export function createGeneTable(
    id,
    species,
    dataset,
    url,
    { correlation = false, select = "none", genes = null } = {},
) {
    const linkGene = makeLinkGene(dataset);
    // Columns to display
    let cols = [
        {
            name: "gene",
            data: "gene",
            title: "Gene",
            orderable: false,
            render: linkGene,
        },
        {
            name: "description",
            data: "description",
            title: "Description",
            orderable: false,
            className: "truncate",
        },
        {
            name: "domains",
            data: "domains",
            title: "Domains",
            orderable: false,
            render: linkDomains,
            className: "truncate",
        },
    ];

    let order;
    if (correlation) {
        cols = cols.concat([
            { name: "pearson", data: "pearson", title: "Pearson's r" },
        ]);

        order = { name: "pearson", dir: "desc" };
    }

    // Gene selection mode
    let selectLayout, selectParam;
    if (select == "multiple") {
        selectParam = true;
    } else if (select == "single") {
        selectParam = { style: "single" };
        selectLayout = { rows: { _: "", 0: "", 1: "" } };
    } else {
        selectParam = false;
    }

    const method = genes && Array.isArray(genes) ? "POST" : "GET";
    const table = new DataTable(`#${id}`, {
        ajax: {
            url: url,
            type: method,
            contentType: "application/json",
            data: function (d) {
                return buildDataQuery(d, species, genes, method);
            },
            dataFilter: filterData,
            dataSrc: "results",
            cache: true,
        },
        pageLength: 10,
        layout: {
            bottomStart: "info",
            bottomEnd: {
                paging: {
                    firstLast: false,
                    previousNext: false,
                },
            },
        },
        processing: true,
        serverSide: true,
        select: selectParam,
        initComplete: function () {
            if (select == "single") {
                // Select first row
                this.api().row(0).select();
            }
        },
        rowId: "gene",
        scrollX: true,
        language: {
            info: "Total entries: _TOTAL_",
            infoEmpty: "Total entries: 0",
            infoFiltered: "",
            select: selectLayout,
        },
        columns: cols,
        order: order,
        createdCell: function (td, cellData) {
            if (td.classList.contains("truncate")) {
                td.setAttribute("title", cellData);
            }
        },
    });
    return table;
}

/**
 * Update DataTable AJAX query to include selected genes.
 *
 * @param {DataTable} table - The DataTable instance to update.
 * @param {Array} genes - Gene names to include.
 */
export function updateGeneTable(table, genes) {
    const species = JSON.parse(table.ajax.params()).species;
    const method = table.settings()[0].ajax.type;
    table.settings()[0].ajax.data = (d) =>
        buildDataQuery(d, species, genes, method);
    table.ajax.reload();
}
