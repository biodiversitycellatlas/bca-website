/**
 * Create interactive DataTables for enrichment analysis results.
 */

import DataTable from "datatables.net-bs5";

import { linkElement, round, roundSignificantDigits } from "./utils.ts";
import { createGeneTable } from "./gene_table.ts";
import { getViewUrl } from "../../utils/urls.ts";

/**
 * Create an external link to a GO term.
 *
 * @param {string} name - The text to display.
 * @param {string} [type="display"] - Rendering mode.
 * @param {Object|null} [row=null] - Row containing the GO term.
 */
function linkExternalGOterm(name, type = "display", row = null) {
    if (type === "display") {
        const term = row?.term;
        const url = "https://amigo.geneontology.org/amigo/term/" + term;
        name = linkElement(name, url);
    }
    return name;
}

 /**
 * Toggles the display of supporting gene details for a selected enrichment term.
 *
 * @param {Event} e - Click event from the DataTable cell.
 * @param {DataTable} table - DataTable instance.
 * @param {string} species - Species identifier.
 * @param {Object} dataset - Dataset slug.
 */
function toggleSupportingGenes(e, table, species, dataset) {
    const tr = e.target.closest("tr");
    const row = table.row(tr);

    // Toggle genes when clicking the genes row
    if (row.child.isShown()) {
        row.child.hide();
    } else {
        const data = row.data();
        const term = data.term.replaceAll(":", "-");
        const childId = `genes-${term}`;

        // Create child table within row
        row.child(`
            <div class="dt-child-container p-1 ps-4 bg-white overflow-hidden">
                <table id="${childId}" class="dt-child-table display compact"></table>
            </div>
        `).show();

        const url = getViewUrl("rest:gene-list");
        createGeneTable(childId, species, dataset, url, {
            genes: data.genes,
        });
    }
}

/**
 * Initialize DataTable to display enrichment analysis results.
 *
 * @param {string} id - HTML element ID to attach the table.
 * @param {string} species - Species identifier.
 * @param {Object} dataset - Dataset reference for linking genes.
 * @param {Object} data - Data object.
 */
export function createEnrichmentTable(id, species, dataset, data) {
    const table = new DataTable(`#${id}_table`, {
        data,
        pageLength: 25,
        scrollX: true,
        columns: [
            { data: "namespace", title: "Namespace" },
            {
                data: "name",
                title: "Name",
                className: "truncate",
                render: linkExternalGOterm,
            },
            {
                data: "pvalue",
                title: "p-value",
                render: roundSignificantDigits,
                className: "dt-nowrap",
            },
            {
                data: "qvalue",
                title: "FDR",
                render: roundSignificantDigits,
                className: "dt-nowrap",
            },
            {
                data: "query_hit_count",
                title: "Genes",
                className:
                    "dt-control d-flex align-items-center gap-1 justify-content-end",
            },
            { data: "background_hit_count", title: "Background" },
            {
                data: "fold_enrichment",
                title: "Fold Enrichment",
                render: round,
            },
            { data: "depth", title: "Depth" },
        ],
        order: [[3, "asc"]],
        createdCell: function (td, cellData) {
            if (td.classList.contains("truncate")) {
                td.setAttribute("title", cellData);
            }
        },
    });

    table.on("click", "tbody td.dt-control", (e) =>
        toggleSuportingGenes(e, table, species, dataset)
    );
}
