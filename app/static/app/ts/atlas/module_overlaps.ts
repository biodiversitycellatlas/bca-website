/**
 * Gene modules: list unique and overlapping genes.
 */

import DataTable from "datatables.net-bs5";

import { getDataPortalUrl } from "../utils/urls.ts";
import { updateDataMenu } from "../buttons/data_dropdown.ts";
import { hideSpinner } from "./plots/plot_container.ts";

/**
 * Load table with shared and unique genes
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {string} dataset - Dataset2 slug to fetch expression data for.
 * @param {Array} modules - Name of gene modules to compare.
 */
export function loadModuleGeneLists(
    id,
    dataset,
    dataset2 = null,
    modules = null,
) {
    if (!modules) return;

    const url = getDataPortalUrl(
        "rest:genemodulesimilaritygenes-list",
        dataset,
        null,
        0,
        {
            list_genes: 1,
            module: modules[0],
            module2: modules[1],
            ...(dataset2 && { dataset2 }),
        },
    );
    updateDataMenu(id, url, "Gene lists");

    const tableId = `#${id}-module-compare-table`;
    new DataTable.Api(tableId).destroy();
    const table = new DataTable(tableId, {
        ajax: {
            url: url,
            dataSrc: "", // display data as returned
            cache: true,
        },
        columns: [
            { title: "Overlap", data: "overlap" },
            { title: "Species", data: "species" },
            { title: "Gene", data: "name" },
            { title: "Description", data: "description" },
            { title: "Domains", data: "domains" },
            { title: "Gene Lists", data: "genelists" },
            { title: "Orthogroup", data: "orthogroup" }
        ],
        responsive: true,
        scrollX: true,
        scrollY: '400px',
        paging: false,
    });
}
