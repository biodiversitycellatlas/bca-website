/**
 * Create interactive gene tables using DataTables.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-select-bs5";

import { makeLinkGene, linkDomains } from "./utils.ts";

function buildDataQuery(data, species, genes) {
    let ordering;
    if (data.order && data.order[0]) {
        const o = data.order[0];
        ordering = (o.dir == "desc" ? "-" : "") + o.name;
    }

    const params = {
        species: species,
        genes: genes,
        // DataTable-associated parameters
        offset: data.start,
        limit: data.length,
        q: data.search.value,
        ordering: ordering,
    };
    return JSON.stringify(params);
}

function filterData(data) {
    const json = JSON.parse(data);
    json.recordsTotal = json.count;
    json.recordsFiltered = json.count;
    json.data = json.list;
    return JSON.stringify(json);
}

/**
 * Initialize a DataTable for displaying gene information.
 * Supports optional correlation columns and selection modes.
 *
 * @param {string} id - Table element ID.
 * @param {Object} dataset - Dataset reference used for linking genes.
 * @param {string} species - Species slug.
 * @param {string} [url=""] - Data source URL for AJAX loading.
 * @param {boolean} [correlation=false] - Whether to include correlation columns.
 * @param {string} [select="multiple"] - Selection mode: "multiple", "single", or "none".
 * @param {Array[string]} [genes=[]] - Array of genes to send to POST.
 */
export function createGeneTable(
    id,
    species,
    dataset,
    url = "",
    correlation = false,
    select = "multiple",
    genes = [],
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
            { name: "spearman", data: "spearman", title: "Spearman's rho" },
        ]);

        order = { name: "pearson_r", dir: "desc" };
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

    const table = new DataTable(`#${id}`, {
        ajax: {
            url: url,
            type: (genes && Array.isArray(genes)) ? "POST" : "GET",
            contentType: "application/json",
            data: function (d) {
                return buildDataQuery(d, species, genes);
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
    //table.settings()[0].ajax.type = "POST";
    const species = JSON.parse(table.ajax.params()).species;
    table.settings()[0].ajax.data = d => buildDataQuery(d, species, genes);
    console.log(table);
    table.ajax.reload();
}
