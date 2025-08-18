/* global $, jQuery */

import { makeLinkGene, parseArray } from "./utils.js";

function buildDataQuery(data) {
    var ordering;
    if (data.order && data.order[0]) {
        const o = data.order[0];
        ordering = (o.dir == "desc" ? "-" : "") + o.name;
    }

    var params = {
        offset: data.start,
        limit: data.length,
        q: data.search.value,
        ordering: ordering,
    };
    return params;
}

function filterData(data) {
    var json = jQuery.parseJSON(data);
    json.recordsTotal = json.count;
    json.recordsFiltered = json.count;
    json.data = json.list;
    return JSON.stringify(json);
}

// Create DataTable
export function createGeneTable(
    id,
    dataset,
    url = "",
    correlation = false,
    select = "multiple",
) {
    let linkGene = makeLinkGene(dataset);
    // Columns to display
    var cols = [
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

    var order;
    if (correlation) {
        cols = cols.concat([
            { name: "pearson", data: "pearson", title: "Pearson's r" },
            { name: "spearman", data: "spearman", title: "Spearman's rho" },
        ]);

        order = { name: "pearson_r", dir: "desc" };
    }

    // Gene selection mode
    var selectLayout, selectParam;
    if (select == "multiple") {
        selectParam = true;
    } else if (select == "single") {
        selectParam = { style: "single" };
        selectLayout = { rows: { _: "", 0: "", 1: "" } };
    } else {
        selectParam = false;
    }

    $(`#${id}`).dataTable({
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
}
