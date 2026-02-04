/**
 * Create interactive gene tables using DataTables.
 */

import $ from "jquery";
import "datatables.net-bs5";
import "datatables.net-select-bs5";

import { makeLinkGene, parseArray } from "./utils.ts";

function buildDataQuery(data) {
    let ordering;
    if (data.order && data.order[0]) {
        const o = data.order[0];
        ordering = (o.dir == "desc" ? "-" : "") + o.name;
    }

    const params = {
        offset: data.start,
        limit: data.length,
        q: data.search.value,
        ordering: ordering,
    };
    return params;
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
 * @param {string} [url=""] - Data source URL for AJAX loading.
 * @param {boolean} [correlation=false] - Whether to include correlation columns.
 * @param {string} [select="multiple"] - Selection mode: "multiple", "single", or "none".
 */
export function createGeneTable(
    id,
    dataset,
    url = "",
    correlation = false,
    select = "multiple",
) {
    const linkGene = makeLinkGene(dataset);
    // Columns to display
    let cols = [
        {
            name: "name",
            data: "name",
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
            render: parseArray,
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

    const table = $(`#${id}`).DataTable({
        ajax: {
            url: url,
            data: buildDataQuery,
            dataFilter: filterData,
            dataSrc: function (json) {
                return json.results;
            },
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
        rowId: "name",
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
            if ($(td).hasClass("truncate")) {
                $(td).attr("title", cellData);
            }
        },
    });
    return table;
}
