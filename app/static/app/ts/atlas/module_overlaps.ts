/**
 * Gene modules: list unique and overlapping genes.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-rowgroup-bs5";

import { getDataPortalUrl } from "../utils/urls.ts";
import { updateDataMenu } from "../buttons/data_dropdown.ts";
import { hideSpinner } from "./plots/plot_container.ts";
import { linkDomains, linkOrthogroup } from "./tables/utils.ts"

function renderCollapsibleRowGroups(rows, group) {
    // Row groups always start expanded
    const collapsed = false;

    // Hide/show rows based on collapsed state
    Array.from(rows.nodes()).forEach(function (r) {
        r.style.display = collapsed ? "none" : "";
    });

    // Create the group row
    const tr = document.createElement("tr");
    tr.dataset.name = group;
    tr.classList.add("group");
    if (collapsed) tr.classList.add("collapsed");

    // Add arrow and text
    const td = document.createElement("td");
    td.colSpan = rows.nodes()[0].cells.length;

    const icon = document.createElement("i");
    const arrow = collapsed ? "right" : "down";
    icon.className = `fa fa-caret-${arrow}`;
    td.appendChild(icon);
    td.appendChild(document.createTextNode(` ${group} (${rows.count()} genes)`));

    tr.appendChild(td);

    // Add click handler to collapse/expand row groups
    tr.addEventListener('click', function () {
        tr.classList.toggle("collapsed");
        const collapsed = tr.classList.contains("collapsed");

        // Update arrow icon
        const icon = td.querySelector("i.fa");
        const arrow = collapsed ? "right" : "down";
        if (icon) icon.className = `fa fa-caret-${arrow}`;

        // Collapse/expand row groups
        rows.every(function () {
            if (this.data().overlap === group) {
                this.node().style.display = collapsed ? "none" : "";
            }
        });
    });
    return tr;
}

/**
 * Load table with shared and unique genes
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {string} dataset - Dataset2 slug to fetch expression data for.
 * @param {Array} modules - Name of gene modules to compare.
 */
export function loadModuleGeneTable(
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
            { title: "Category", data: "overlap", visible: false },
            { title: "Gene", data: "name" },
            { title: "Description", data: "description", visible: false },
            { title: "Domains", data: "domains", render: linkDomains },
            { title: "Gene Lists", data: "genelists" },
            { title: "Orthogroup", data: "orthogroup", render: linkOrthogroup },
        ],
        orderFixed: [[0, "asc"]],
        rowGroup: {
            dataSrc: "overlap",
            startRender: renderCollapsibleRowGroups,
        },
        responsive: true,
        scrollX: true,
        scrollY: "400px",
        paging: false,
    });
}
