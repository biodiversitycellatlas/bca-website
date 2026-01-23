/**
 * Dataset statistics and plots.
 */

import $ from "jquery";

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
