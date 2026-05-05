/**
 * Create interactive DataTables for results from an enrichment analysis.
 */

import $ from "jquery";
import "datatables.net-bs5";
import "datatables.net-select-bs5";

import { makeLinkGene, round, parseArray } from "./utils.ts";

/**
 * Initialize a DataTable for displaying marker gene information.
 *
 * @param {string} id - HTML element ID to attach the table.
 * @param {Object} dataset - Dataset reference for linking genes.
 * @param {string} url - URL to fetch gene marker data.
 * @param {Object} payload - Data object sent as the POST request body.
 */
export function createEnrichmentTable(id, dataset, url, payload) {
    const linkGene = makeLinkGene(dataset);
    console.log(url);
    $(`#${id}_table`).dataTable({
        ajax: {
            url: url,
            type: "POST",
            contentType: "application/json",
            data: function () {
                return JSON.stringify(payload);
            },
            dataSrc: function (json) {
                return json;
            },
        },
        pageLength: 25,
        scrollX: true,
        columns: [
            { data: "namespace", title: "Namespace" },
            { data: "term", title: "GO term" },
            { data: "name", title: "Name", className: "truncate", },
            { data: "enrichment", title: "Enrichment" },
            { data: "depth", title: "Depth" },
            { data: "pvalue", title: "p-value", render: round },
            { data: "qvalue", title: "q-value", render: round },
            { data: "query_hit_count", title: "Query hit count" },
            { data: "query_count", title: "Query count" },
            { data: "background_hit_count", title: "Background hit count" },
            { data: "background_count", title: "Background count" },
            { data: "genes", title: "Genes", render: parseArray },
        ],
        //order: [[5, "des"]],
        createdCell: function (td, cellData) {
            if ($(td).hasClass("truncate")) {
                $(td).attr("title", cellData);
            }
        },
    });
}
