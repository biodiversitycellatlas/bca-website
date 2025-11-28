/**
 * Tree of Life visualization
 */

/* global vegaEmbed */

import { COLOR_SCALE } from "./metacell_heatmap.js";

export let viewSimilarityPlot;

let lastClicked = null;

/**
 * Render plot of gene module similarity for a given dataset.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {Array} data - Array of objects with similarity across gene modules.
 * @param {function} clickListener - Function to call when user clicks in the plot.
 */
export function createSimilarityPlot(id, data, clickListener = null) {
    const chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        description: "Bubble chart of module similarities",
        data: { values: data },
        width: "container",
        height: "container",
        transform: [
            {
                joinaggregate: [
                    { op: "distinct", field: "module", as: "count" },
                ],
            },
        ],
        mark: {
            type: "rect",
            tooltip: { content: "data" },
            cursor: clickListener ? "pointer" : "cursor",
        },
        encoding: {
            x: {
                field: "module",
                type: "ordinal",
                axis: {
                    labels: true,
                    labelExpr:
                        "data('data_0')[0].count < 30 ? datum.label : ''",
                    ticks: false,
                    domain: false,
                    title: "Gene Modules",
                },
            },
            y: {
                field: "module2",
                type: "ordinal",
                axis: {
                    labels: true,
                    labelExpr:
                        "data('data_0')[0].count < 30 ? datum.label : ''",
                    ticks: false,
                    domain: false,
                    title: "Gene Modules",
                },
            },
            size: {
                field: "similarity",
                type: "quantitative",
                title: "Similarity",
            },
            color: {
                field: "similarity",
                type: "quantitative",
                scale: { range: COLOR_SCALE },
                title: "Similarity",
            },
            text: { field: "similarity", type: "quantitative", format: "d'%'" },
        },
        view: { stroke: null },
    };

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => {
            viewSimilarityPlot = res.view;

            // Add click event listener to update other components
            if (!clickListener) return;
            viewSimilarityPlot.addEventListener("click", (event, item) => {
                const datum = item?.datum ?? null;
                // Only call listener if clicking on different datum
                if (datum && datum !== lastClicked) {
                    lastClicked = datum;
                    clickListener(event, item);
                }
            });
        })
        .catch(console.error);
}
