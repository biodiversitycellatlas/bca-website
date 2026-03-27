/**
 * Gene modules: list unique and overlapping genes.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-rowgroup-bs5";

import { getViewUrl } from "../utils/urls.ts";
import { updateDataMenu } from "../buttons/data_dropdown.ts";
import {
    linkElement,
    linkGene,
    linkGeneModule,
    linkGeneLists,
    linkDomains,
    linkOrthogroups,
} from "./tables/utils.ts";

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

    // Add label with arrow to indicate if group is collapsed
    const div = document.createElement("div");
    div.className =
        "d-flex flex-wrap justify-content-between align-items-center";

    const [category, dataset, module] = group.split("_");
    const label = document.createElement("span");

    // Add gene count
    const icon = document.createElement("i");
    const arrow = collapsed ? "right" : "down";
    icon.className = `fa fa-caret-${arrow}`;

    const count = document.createElement("span");
    count.innerHTML = `${icon.outerHTML} ${rows.count()} ${category} genes`;
    count.className = "position-sticky start-0 ps-1";
    div.appendChild(count);

    // Add group label
    if (dataset && module) {
        label.innerHTML = `${datasetHtml[dataset]} • Gene module: ${linkGeneModule(dataset, module)}`;
        label.className = "position-sticky end-0 pe-1";
        div.appendChild(label);
    }

    // Add click handler to collapse/expand row groups
    td.appendChild(div);
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

function renderLinkGene(
    gene,
    type = "display",
    row = null,
    dataset1 = null,
    dataset2 = null,
) {
    if (type === "display") {
        const dataset = row?.dataset;
        if (dataset) {
            gene = linkGene(dataset, gene, type, row);
        } else {
            const d1Label = dataset1.split("-").slice(2).join(" ");
            const d2Label = dataset2.split("-").slice(2).join(" ");
            const d1Link = linkElement(
                d1Label,
                getViewUrl("atlas_gene", { dataset: dataset1, gene }),
            );
            const d2Link = linkElement(
                d2Label,
                getViewUrl("atlas_gene", { dataset: dataset2, gene }),
            );
            gene = `${gene} (${d1Link}, ${d2Link})`;
        }
    }
    return gene;
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
    dataset1html,
    dataset2html = null,
    data = null,
) {
    if (!modules) return;

    console.log(data);
    const dataset1 = data.dataset,
        dataset2 = data.dataset2;

    console.log(data);
    // Update module information
    document.getElementById(`${id}-dataset-module`).innerHTML =
        `${linkGeneModule(dataset1, data.module)} module`;
    document.getElementById(`${id}-dataset-module-genes`).innerHTML =
        `Genes: ${data.shared_genes_module} shared, ${data.unique_genes_module} unique`;
    document.getElementById(`${id}-dataset2-module`).innerHTML =
        `${linkGeneModule(dataset2, data.module2)} module`;
    document.getElementById(`${id}-dataset2-module-genes`).innerHTML =
        `Genes: ${data.shared_genes_module2} shared, ${data.unique_genes_module2} unique`;
    document.getElementById(`${id}-jaccard`).innerHTML =
        `Jaccard similarity index: ${Math.round(data.similarity * 100)}%`;

    const url = getViewUrl("rest:genemodulesimilaritygenes-list", {
        dataset: dataset1,
        limit: 0,
        list_genes: 1,
        module: data.module,
        module2: data.module2,
        dataset2,
    });
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
            {
                title: "Gene",
                data: "gene",
                render: function (gene, type, row) {
                    return renderLinkGene(gene, type, row, dataset1, dataset2);
                },
            },
            {
                title: "Description",
                data: "description",
                visible: true,
                className: "truncate",
            },
            { title: "Domains", data: "domains", render: linkDomains },
            { title: "Gene lists", data: "genelists", render: linkGeneLists },
            {
                title: "Orthogroups",
                data: "orthogroups",
                render: linkOrthogroups,
            },
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
    return table;
}
