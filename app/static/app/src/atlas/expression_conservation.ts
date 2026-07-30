/**
 * Expression conservation table and single-ortholog expression plot.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-select-bs5";

import { getViewUrl } from "../utils/urls.ts";
import { appendDataMenu, updateDataMenu } from "../buttons/data_dropdown.ts";
import { createExpressionBubblePlot } from "./plots/expression_plot.ts";
import { linkDomains, makeLinkGene, round } from "./tables/utils.ts";
import { showSpinner, hideSpinner, clearContainer } from "./plots/plot_container.ts";

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
 * Create an expression conservation DataTable for a given gene.
 */
function createExpressionConservationTable(id, dataset, gene) {
    const apiURL = getViewUrl("rest:expressionconservation-list", { gene });
    appendDataMenu(id, apiURL, "Expression conservation (current page)");

    const table = new DataTable(`#${id}_table`, {
        ajax: {
            url: apiURL,
            data: buildDataQuery,
            dataFilter: filterData,
            dataSrc: "results",
            cache: true,
        },
        pageLength: 10,
        layout: {
            bottomStart: "info",
            bottomEnd: { paging: { firstLast: false, previousNext: false } },
        },
        processing: true,
        serverSide: true,
        select: { style: "single" },
        initComplete: function () { this.api().row(0).select(); },
        scrollX: true,
        language: {
            info: "Total entries: _TOTAL_",
            infoEmpty: "Total entries: 0",
            infoFiltered: "",
            select: { rows: { _: "", 0: "", 1: "" } },
        },
        columns: [
            { name: "dataset", data: "dataset_link", title: "Dataset" },
            { name: "gene", data: "gene", title: "Gene", orderable: false, render: makeLinkGene() },
            { name: "description", data: "description", title: "Description", orderable: false, className: "truncate" },
            { name: "domains", data: "domains", title: "Domains", orderable: false, render: linkDomains, className: "truncate" },
            { name: "conservation_score", data: "conservation_score", title: "Expression conservation", render: round },
        ],
        order: { name: "conservation_score", dir: "desc" },
        createdCell: function (td, cellData) {
            if (td.classList.contains("truncate")) {
                td.setAttribute("title", cellData);
            }
        },
    });
    return table;
}

/**
 * Fetch expression data for a single ortholog and render a bubble plot.
 */
function loadOrthologExpression(id, dataset, gene, row) {
    const apiURL = getViewUrl("rest:metacellgeneexpression-list", {
        dataset: row.dataset,
        genes: row.gene,
        limit: 0,
    });
    updateDataMenu(id, apiURL, "Expression conservation (plot data)");

    clearContainer(id);
    showSpinner(id);

    // Update header above plot
    const linkGene = makeLinkGene()(row.gene, "display", null, row);
    document.getElementById(`${id}_heading`).innerHTML = `${row.dataset_link} • ${linkGene}`;

    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            if (data.length === 0) {
                document.getElementById(`${id}-plot`).innerHTML = `
                    <p class='text-muted'>
                        <i class='fa fa-circle-exclamation'></i>
                        No expression data for <b>${row.gene}</b>.
                    </p>
                `;
            } else {
                createExpressionBubblePlot(`#${id}-plot`, row.gene, data);
            }
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        })
        .finally(() => {
            hideSpinner(id);
        });
}

/**
 * Load expression conservation interface.
 */
export function loadExpressionConservation(id, dataset, gene) {
    const table = createExpressionConservationTable(id, dataset, gene);

    // Plot expression when selecting a new row in the table
    table.on("select", function (e, dt, type) {
        if (type === "row") {
            const selected = dt.rows({ selected: true }).data();
            if (selected && selected.length > 0) {
                const row = selected[0];
                loadOrthologExpression(id, dataset, gene, row);
            }
        }
    });

    hideSpinner(id);
}
