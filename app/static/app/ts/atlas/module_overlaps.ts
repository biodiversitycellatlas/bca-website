/**
 * Gene modules: list unique and overlapping genes.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-rowgroup-bs5";

import { getDataPortalUrl } from "../utils/urls.ts";
import { updateDataMenu } from "../buttons/data_dropdown.ts";
import { hideSpinner } from "./plots/plot_container.ts";
import { makeLinkGene, linkDomains, linkOrthogroup } from "./tables/utils.ts";

function toggleRowGroupVisibility(rows, collapsed, group = null) {
    rows.every(function () {
        if (group === null || this.data().overlap === group) {
            this.node().style.display = collapsed ? "none" : "";
        }
    });
}

function renderCollapsibleRowGroups(rows, group, datasetHtml) {
    // Row groups always start expanded
    const collapsed = false;
    toggleRowGroupVisibility(rows, collapsed);

    // Create the group row with position-sticky
    const tr = document.createElement("tr");
    tr.dataset.name = group;
    tr.classList.add("group");

    const td = document.createElement("td");
    td.className = "position-sticky top-0";
    td.colSpan = rows.nodes()[0].cells.length;

    // Add group label with arrow to indicate if group is collapsed
    const div = document.createElement("div");
    div.className =
        "d-flex flex-wrap justify-content-between align-items-center";

    const icon = document.createElement("i");
    const arrow = collapsed ? "right" : "down";
    icon.className = `fa fa-caret-${arrow}`;

    const [category, dataset, module] = group.split("_");
    const groupLabel = category;
    const label = document.createElement("span");

    const labelHtml =
        dataset && module
            ? `${datasetHtml[dataset]} ${module}`
            : `Intersecting genes`;
    label.innerHTML = `${icon.outerHTML} ${labelHtml}`;

    label.className = "position-sticky start-0 ps-1";
    div.appendChild(label);

    // Add gene count to the right side (as sticky element)
    const count = document.createElement("span");
    count.innerHTML = `${rows.count()} ${category} genes`;
    count.className = "position-sticky end-0 pe-1";
    div.appendChild(count);
    td.appendChild(div);

    // Add click handler to collapse/expand row groups
    tr.appendChild(td);
    tr.addEventListener("click", function () {
        tr.classList.toggle("collapsed");
        const collapsed = tr.classList.contains("collapsed");

        // Update arrow icon
        const arrow = collapsed ? "right" : "down";
        td.querySelector("i.fa").className = `fa fa-caret-${arrow}`;

        // Collapse/expand row groups
        toggleRowGroupVisibility(rows, collapsed, group);
    });
    return tr;
}

/**
 * Load table with shared and unique genes
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset1 - Dataset slug to fetch expression data for.
 * @param {string} dataset2 - Dataset 2 slug to fetch expression data for.
 * @param {Array} modules - Name of gene modules to compare.
 */
export function loadModuleGeneTable(
    id,
    dataset1,
    dataset1html,
    dataset2 = null,
    dataset2html = null,
    modules = null,
) {
    if (!modules) return;

    const url = getDataPortalUrl(
        "rest:genemodulesimilaritygenes-list",
        dataset1,
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
            { title: "Gene", data: "name", render: makeLinkGene() },
            {
                title: "Description",
                data: "description",
                visible: true,
                className: "truncate",
            },
            { title: "Domains", data: "domains", render: linkDomains },
            {
                title: "Gene lists",
                data: "genelists",
                render: (value) => value.join(", "),
            },
            { title: "Orthogroup", data: "orthogroup", render: linkOrthogroup },
        ],
        orderFixed: [[0, "asc"]],
        rowGroup: {
            dataSrc: "overlap",
            startRender: function (rows, group) {
                // Create dictionary with HTML of both datasets
                const datasetHtml = {
                    [dataset1]: dataset1html,
                    ...(dataset2 ? { [dataset2]: dataset2html } : {}),
                };
                return renderCollapsibleRowGroups(rows, group, datasetHtml);
            },
        },
        responsive: true,
        scrollX: true,
        scrollY: "400px",
        paging: false,
        language: { search: "", searchPlaceholder: "Search table..." },
    });
}
