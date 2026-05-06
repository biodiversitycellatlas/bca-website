/**
 * Create interactive DataTables for results from an enrichment analysis.
 */

import $ from "jquery";
import "datatables.net-bs5";
import "datatables.net-responsive-bs5";

import { linkElement, makeLinkGene, roundSignificantDigits, parseArray } from "./utils.ts";

function linkExternalGOterm(term) {
    const url = "https://amigo.geneontology.org/amigo/term/" + term;
    return linkElement(term, url);
}

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
    const linkGeneArray = (genes) => {
        if (!genes) return "";
        if (Array.isArray(genes)) {
            return genes.map(g => linkGene(g)).join(', ');
        }
        return linkGene(genes);
    };

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
            { data: "term", title: "GO term", render: linkExternalGOterm },
            { data: "namespace", title: "Namespace" },
            { data: "name", title: "Name", className: "truncate", },
            { data: "pvalue", title: "p-value", render: roundSignificantDigits, className: "dt-nowrap" },
            { data: "qvalue", title: "FDR", render: roundSignificantDigits, className: "dt-nowrap" },
            { data: "query_hit_count", title: "Query" },
            { data: "background_hit_count", title: "Background" },
            { data: "genes", title: "Genes", render: linkGeneArray },
            { data: "enrichment", title: "Enrichment" },
            { data: "depth", title: "Depth" },
            { data: "query_count", title: "Query count" },
            { data: "background_count", title: "Background count" },
        ],
        order: [[5, "asc"]],
        createdCell: function (td, cellData) {
            if ($(td).hasClass("truncate")) {
                $(td).attr("title", cellData);
            }
        },
        responsive: true,
    });
}
