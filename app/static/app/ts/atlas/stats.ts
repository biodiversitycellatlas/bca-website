/**
 * Dataset statistics and plots.
 */

import $ from "jquery";
import "datatables.net-bs5";

import { getDataPortalUrl } from "../utils/urls.ts";
import { createStatsPlot } from "./plots/stats_plot.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";

/**
 * Animate number incrementing from 0 up to the target value.
 *
 * @param {string} id - DOM element selector to update (e.g., '#counter').
 * @param {number} target - Target number.
 */
function animateNumber(id, target) {
    let val = 0;

    // Increment value at a fixed interval
    const time = 15;
    const duration = 250;
    const increment = Math.max(Math.floor(target / (duration / time)), 1);

    const interval = setInterval(function () {
        val += increment;
        if (val >= target) {
            val = target;
            clearInterval(interval);
        }
        $(id).text(val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " "));
    }, time);
}

/**
 * Fetch dataset statistics and update numeric counters on the page.
 *
 * @param {string} dataset - Dataset name.
 */
export function loadDatasetStats(dataset) {
    const urls = {
        info: getDataPortalUrl("rest:dataset-detail", dataset),
        stats: getDataPortalUrl("rest:stats-detail", dataset),
        counts: getDataPortalUrl("rest:metacellcount-list", dataset),
    };

    appendDataMenu("info", urls, [
        "Dataset information",
        "Summary statistics",
        "Metacell counts",
    ]);

    fetch(urls.stats)
        .then((response) => response.json())
        .then((data) => {
            animateNumber("#n_cells", data.cells);
            animateNumber("#n_metacells", data.metacells);
            animateNumber("#n_umis", data.umis);
            animateNumber("#n_genes", data.genes);
        })
        .catch((error) => console.error("Error:", error));
}

/**
 * Render per-metacell statistics plots.
 *
 * @param {string} dataset - Dataset name.
 */
export function renderStatsPlots(dataset) {
    const url = getDataPortalUrl("rest:metacellcount-list", dataset, null, 0);
    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            createStatsPlot(
                "#metacell-cells-plot",
                data,
                "cells",
                "Cells per metacell",
                "Cell count",
            );
            createStatsPlot(
                "#metacell-umis-plot",
                data,
                "umis",
                "UMIs per metacell",
                "UMI count",
            );
        })
        .catch((error) => console.error("Error:", error));
}

/**
 * Fetch dataset statistics and update numeric counters on the page.
 *
 * @param {string} dataset - Dataset name.
 */
export function loadGeneModuleSize(dataset) {
    const url = getDataPortalUrl("rest:genemodule-list", dataset);

    fetch(url)
        .then((response) => response.json())
        .then((data) => animateNumber("#n_modules", data.count))
        .catch((error) => console.error("Error:", error));
}

/**
 * Render per-metacell statistics plots.
 *
 * @param {string} dataset - Dataset name.
 */
export function renderGeneModuleStatsPlots(dataset) {
    const url = getDataPortalUrl("rest:genemodule-list", dataset, null, 0, {
        order_by_gene_count: 1,
    });
    appendDataMenu("modules", url, "Gene modules");

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            createStatsPlot(
                "#modules-plot",
                data,
                "gene_count",
                "Genes per module",
                "Gene count",
                false,
            );
        })
        .catch((error) => console.error("Error:", error));
}

function renderGeneModuleLink(dataset, module, text = module) {
    const url = getDataPortalUrl("gene_module_entry", dataset, null, null, {
        gene_module: module,
    });
    return `<a href="${url}">${text}</a>`;
}

function renderGeneLink(dataset, gene, text = gene) {
    if (!gene) return "";

    const url = getDataPortalUrl("atlas_gene", dataset, gene);
    return `<a class="small" href="${url}">${text}</a>`;
}

export function renderGeneModuleTable(id, dataset) {
    const url = getDataPortalUrl("rest:genemodule-list", dataset, null, 0, {
        order_by_gene_count: 1,
    });

    // Render n columns for top transcription factors
    const topTFs = (n) =>
        Array.from({ length: n }, (_, i) => ({
            data: "top_tf",
            render: (d) => renderGeneLink(dataset, d[i]),
        }));

    $(`#${id}`).DataTable({
        ajax: { url: url, dataSrc: "" },
        columns: [
            {
                data: "module",
                render: (d) => renderGeneModuleLink(dataset, d),
            },
            { data: "gene_count" },
            ...topTFs(5),
        ],
        responsive: true,
        pageLength: -1,
        paging: false,
        info: false,
        scrollY: "190px",
        scrollX: true,
        language: { search: "", searchPlaceholder: "Search table..." },
        order: [[1, "des"]],
    });
}
