/**
 * Visualize SAMap comparisons between datasets.
 */

import DataTable from "datatables.net-bs5";

import { getViewUrl } from "../utils/urls.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { hideSpinner } from "./plots/plot_container.ts";
import { createSAMapSankey } from "./plots/samap_sankey_plot.ts";
import { createSAMapHeatmap } from "./plots/samap_heatmap.js";
import { linkDomains, makeLinkGene } from "./tables/utils.ts";

/**
 * Update parameter and reload page.
 *
 * @param {string} param - Parameter name to set.
 * @param {string} value - Value.
 */
export function updateParam(param, value) {
    const url = new URL(window.location);
    url.searchParams.set(param, value);
    window.location.href = url.href;
}

/**
 * Navigate to new URL query parameters based on form data.
 * Maintains query when changing only one value.
 *
 * @param {HTMLFormElement} form - The submitted form element.
 * @param {Event} event - The submit event.
 */
function modifyFormQuery(form, event) {
    event.preventDefault();

    // Modify form URL
    const formData = new FormData(form);
    const url = new URL(form.action);
    for (const [key, value] of formData.entries()) {
        url.searchParams.set(key, value);
    }
    window.location.href = url.href;
}

/**
 * When submitting form, modify query params.
 */
export function handleFormSubmit() {
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            modifyFormQuery(form, event);
        });
    });
}

function fetchGeneInfo(species, genes) {
    const url = getViewUrl("rest:gene-list") + "?limit=0";
    const body = JSON.stringify({ species, genes });

    const data = fetch(url, {
            method: "POST",
            body: body,
            headers: { "Content-Type": "application/json" },
        })
        .then(response => response.json())
        .then(data => {
            const geneInfo = {};
            data.forEach(gene => { geneInfo[gene.gene] = gene; });
            return geneInfo;
        });
    return data;
}

function createTable(id, rows, dataset, dataset2) {
    // Destroy table if it exists
    const tableId = `#${id}-cell-type-compare-table`;
    new DataTable.Api(tableId).destroy();

    const table = new DataTable(tableId, {
        data: rows,
        columns: [
            { title: "Gene 1", data: "gene1_gene", render: makeLinkGene(dataset) },
            { title: "Description 1", data: "gene1_description", className: "truncate" },
            { title: "Domains 1", data: "gene1_domains", render: linkDomains, className: "truncate" },
            { title: "Gene 2", data: "gene2_gene", render: makeLinkGene(dataset2) },
            { title: "Description 2", data: "gene2_description", className: "truncate" },
            { title: "Domains 2", data: "gene2_domains", render: linkDomains, className: "truncate" },
        ],
        // orderFixed: [[0, "asc"]],
        responsive: true,
        scrollX: true,
        scrollY: "400px",
        paging: false,
        language: { search: "", searchPlaceholder: "Search table..." },
    });
    return table;
}

function createGenePairsTable(id, genePairs, species, species2, dataset, dataset2) {
    const genes = [...new Set(genePairs.map(([gene1]) => gene1))];
    const genes2 = [...new Set(genePairs.map(([, gene2]) => gene2))];

    return Promise.all([
        fetchGeneInfo(species, genes),
        fetchGeneInfo(species2, genes2),
    ]).then(([geneInfo1, geneInfo2]) => {
        const rows = genePairs.map(([gene1, gene2]) =>
            Object.fromEntries([
                ...Object.entries(geneInfo1[gene1]).map(([key, value]) => [`gene1_${key}`, value]),
                ...Object.entries(geneInfo2[gene2]).map(([key, value]) => [`gene2_${key}`, value]),
            ])
        );
        createTable(id, rows, dataset, dataset2);
    });
}

function updateCellTypesLabels(id, metacellType, metacellType2) {
    document.getElementById(`${id}-metacell-type`).textContent = metacellType;
    document.getElementById(`${id}-metacell2-type`).textContent = metacellType2;
}

/**
 * Fetch and display metacell type similarity between datasets.
 * Renders a Sankey plot showing cell-type correspondences.
 *
 * @param {string} id - HTML element ID prefix for the plot container
 * @param {string} label - Label for the first dataset
 * @param {string} dataset - Name of the first dataset
 * @param {string} label2 - Label for the second dataset
 * @param {string} dataset2 - Name of the second dataset
 */
export function initSAMap(id, label, dataset, species, label2, dataset2, species2) {
    const url = getViewUrl("rest:metacelltypesimilarity-list", {
        dataset,
        dataset2,
        min_samap: document.getElementById("min_samap").value,
        limit: 0,
    });

    const heatmap = document.getElementById("plot").value == "heatmap";
    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            if (!data.length) {
                const plot = document.getElementById(`${id}-plot`);
                plot.parentElement.parentElement.innerHTML = `
                    <p class="text-muted">
                        <i class="fa fa-circle-exclamation"></i>
                        No data available for the selected datasets.
                    </p>
                `;
            } else if (heatmap) {
                return createSAMapHeatmap(`#${id}-plot`, data, label, label2);
            } else {
                return createSAMapSankey(`#${id}-plot`, data, label, label2);
            }
        })
        .then((view) => {
            // Update table when clicking valid plot values
            view.addEventListener("click", (event, item) => {
                if (!item) return;
                if (!item.datum.samap_gene_pairs) return;

                updateCellTypesLabels(
                    id,
                    item.datum.metacell_type,
                    item.datum.metacell2_type,
                );
                createGenePairsTable(
                    id,
                    item.datum.samap_gene_pairs,
                    species,
                    species2,
                    dataset,
                    dataset2,
                );
            });
        })
        .catch((error) => console.error("Error fetching data:", error))
        .finally(() => hideSpinner(id));

    appendDataMenu(id, url, "SAMap scores");
}
