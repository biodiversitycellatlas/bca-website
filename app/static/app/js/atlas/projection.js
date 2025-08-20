/**
 * Visualize Metacell projection.
 */

/* global $ */

import { getDataPortalUrl } from "../utils/urls.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";
import { hideSpinner } from "../plots/plot_container.js";
import {
    createMetacellProjection,
    viewMetacellProjection,
} from "../plots/metacell_scatterplot.js";

/**
 * Toggle gene selection input.
 * Updates URL if a gene is currently selected.
 *
 * @param {string} id - HTML element ID prefix for the gene selectize input
 */
function toggleGeneSelectize(id) {
    $('input[name="color_by"]').change(function () {
        let elem = $(`#${id}_gene_selection`)[0].selectize;
        this.id.includes("expression") ? elem.enable() : elem.disable();

        let url = new URL(window.location.href);
        if (url.searchParams.has("gene")) {
            url.searchParams.delete("gene");
            url.hash = `#${id}`;
            window.location.href = url;
        }
    });
}

/**
 * Initialize all checkboxes so their value reflects their checked state.
 */
function initCheckboxSelect() {
    $('input[type="checkbox"]').each(function () {
        this.value = this.checked;
        this.setAttribute("onclick", "this.value = this.checked;");
    });
}

/**
 * Returns selected metacells in the brush.
 *
 * @returns {string[]} Array of selected metacell names
 */
function getSelectedMetacells() {
    let view = viewMetacellProjection;

    // Get selection brush
    let brush = view.signal("brush");
    if ($.isEmptyObject(brush)) {
        // Brush not available
        return [];
    }
    let [minX, maxX] = brush.x;
    let [minY, maxY] = brush.y;

    // Get data within selection brush
    let data = view.data("mc_data");
    let x, y;
    let metacells = [];
    for (let i = 0; i < data.length; i++) {
        x = data[i].x;
        y = data[i].y;
        if (minX <= x && x <= maxX && minY <= y && y <= maxY) {
            metacells.push(data[i].name);
        }
    }
    return metacells;
}

/**
 * Navigates to the given URL with selected metacells.
 * Raise alert if no metacells are selected.
 *
 * @param {string|URL} url - URL containing METACELL_PLACEHOLDER
 */
function handleSelectedMetacell(url) {
    let metacells = getSelectedMetacells();
    if (metacells.length >= 1) {
        url = url.toString().replace("METACELL_PLACEHOLDER", metacells);
        window.location.href = url;
    } else {
        alert(
            "No metacells selected.\n\nClick and drag to select metacells in the scatterplot.",
        );
    }
}

/**
 * List markers for selected metacells.
 *
 * @param {string} dataset - Name of the dataset to fetch markers for
 */
function listMarkers(dataset) {
    $("#list_markers").on("click", function () {
        let url =
            getDataPortalUrl("atlas_markers", dataset) +
            "?metacells=METACELL_PLACEHOLDER";
        handleSelectedMetacell(url);
    });
}

/**
 * Filter the heatmap by selected metacells.
 */
function filterHeatmap() {
    $("#filter_heatmap").on("click", function () {
        let url = new URL(window.location.href);
        url.searchParams.set("metacells", "METACELL_PLACEHOLDER");
        url.hash = "expression";
        handleSelectedMetacell(url);
    });
}

/**
 * Load and render a metacell projection plot with optional gene coloring.
 * Also sets up interactivity like marker listing and heatmap filtering.
 *
 * @param {string} id - HTML element ID prefix for the plot
 * @param {string} dataset - Dataset name
 * @param {string} label - Label for dataset in the UI
 * @param {string|null} gene - Gene to color by (or null for metacell type)
 */
export function initProjection(id, dataset, label, gene) {
    initCheckboxSelect();
    toggleGeneSelectize("{{id}}"); // Toggle state of gene selectize element
    listMarkers(dataset);
    filterHeatmap();

    let urls = {
        sc_data: getDataPortalUrl("rest:singlecell-list", dataset, gene, 0),
        mc_data: getDataPortalUrl("rest:metacell-list", dataset, gene, 0),
        mc_links: getDataPortalUrl("rest:metacelllink-list", dataset, null, 0),
    };

    appendDataMenu(id, urls, [
        "Single-cell data",
        "Metacell data",
        "Metacell links",
    ]);

    Promise.all(
        Object.entries(urls).map(([key, url]) =>
            fetch(url)
                .then((res) => (res.ok ? res.json() : null))
                .then((data) => ({ key, data })),
        ),
    )
        .then((results) => {
            // Combine results into a dictionary
            const data = results.reduce((acc, { key, data }) => {
                acc[key] = data;
                return acc;
            }, {});

            if (!data["sc_data"] && !data["mc_data"]) {
                // Show informative message that no expression data is available
                let plot = document.getElementById(`${id}-plot`);
                plot.innerHTML = `<p class='text-muted'><i class='fa fa-circle-exclamation'></i> No <b>${gene}</b> expression for <i>${label}</i>.</p>`;
                plot.style.removeProperty("aspect-ratio");

                // Remove plot buttons
                document.getElementById(`${id}-plot-ui`).style.display = "none";
            } else {
                let color_by_metacell_type = gene === null;
                createMetacellProjection(
                    `#${id}-plot`,
                    dataset,
                    data,
                    color_by_metacell_type,
                    gene,
                );
            }
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
            hideSpinner(id);
        });
}
