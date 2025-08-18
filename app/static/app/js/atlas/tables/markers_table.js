/* global $ */

import { makeLinkGene, round, parseArray } from "./utils.js";

// Create DataTable
export function createMarkersTable(id, dataset, url) {
    let linkGene = makeLinkGene(dataset);
    $(`#${id}_table`).dataTable({
        ajax: {
            url: url,
            dataSrc: function (json) {
                return json;
            },
        },
        pageLength: 25,
        scrollX: true,
        columns: [
            { data: "name", title: "Gene ID", render: linkGene },
            {
                data: "description",
                title: "Description",
                className: "truncate",
            },
            {
                data: "domains",
                title: "Domains",
                render: parseArray,
                className: "truncate",
            },
            { data: "genelists", title: "Gene lists", className: "truncate" },
            { data: "fg_sum_umi", title: "Total UMIs" },
            { data: "umi_perc", title: "UMI %", render: round },
            { data: "fg_mean_fc", title: "Mean FC", render: round },
            { data: "fg_median_fc", title: "Median FC", render: round },
        ],
        order: [[5, "des"]],
        createdCell: function (td, cellData) {
            if ($(td).hasClass("truncate")) {
                $(td).attr("title", cellData);
            }
        },
    });
}
