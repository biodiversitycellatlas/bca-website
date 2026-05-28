/**
 * Semantic similarity plot.
 */

import vegaEmbed from "vega-embed";

import { COLOR_SCALE } from "./metacell_heatmap.ts";

export let viewSimilarityPlot;

/**
 * Render plot of gene module similarity for a given dataset.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {Array} data - Array of semantic similarity data.
 */
export function createSemanticSimilarityPlot(id, data) {
    const chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        description: "GO term semantic similarity plot",
        data: { values: data },
        width: "container",
        height: "container",
        transform: [
            { calculate: "datum.similarity_coords[0]", as: "x" },
            { calculate: "datum.similarity_coords[1]", as: "y" },
            { calculate: "-log(datum.qvalue)", as: "sig" },
        ],
        mark: {
            type: "circle",
            tooltip: { content: "data" },
        },
        encoding: {
            x: { field: "x", type: "quantitative", title: "" },
            y: { field: "y", type: "quantitative", title: "" },
            color: {
                field: "sig",
                type: "quantitative",
                scale: { range: COLOR_SCALE },
                title: "-log(qvalue)",
            },
        },
        params: [
            {
                name: "zoom",
                select: "interval",
                bind: "scales",
            },
        ],
    };

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => {
            viewSimilarityPlot = res.view;
        })
        .catch(console.error);
}
