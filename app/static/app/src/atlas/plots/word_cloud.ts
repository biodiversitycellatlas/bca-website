/**
 * Word cloud.
 */

import vegaEmbed from "vega-embed";

import { COLOR_SCALE } from "./metacell_heatmap.ts";

export let viewWordCloud;

/**
 * Render world cloud.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {Array} data - Array of data.
 */
export function createWordCloud(id, data) {
    const words = data.map((d) => d.name);

    const chart = {
        $schema: "https://vega.github.io/schema/vega/v6.json",
        description: "GO term word cloud",
        width: { signal: "containerSize()[0]" },
        height: { signal: "containerSize()[1]" },
        autosize: { type: "fit", resize: true },

        data: {
            name: "table",
            values: words,
            transform: [
                {
                    type: "countpattern",
                    field: "data",
                    case: "upper",
                    pattern: "[\\w']{3,}",
                    stopwords: "(non)",
                },
            ],
        },
        mark: { type: "point", tooltip: { content: "data" } },
        scales: [
            {
                name: "color",
                type: "ordinal",
                domain: { data: "table", field: "text" },
                range: COLOR_SCALE,
            },
        ],

        marks: [
            {
                type: "text",
                from: { data: "table" },
                encode: {
                    enter: {
                        text: { field: "text" },
                        align: { value: "center" },
                        baseline: { value: "alphabetic" },
                        fill: { scale: "color", field: "text" },
                    },
                    update: { fillOpacity: { value: 1 } },
                    hover: { fillOpacity: { value: 0.5 } },
                },
                transform: [
                    {
                        type: "wordcloud",
                        text: { field: "text" },
                        size: [{ signal: "width" }, { signal: "height" }],
                        fontSize: { field: "datum.count" },
                        fontSizeRange: [12, 40],
                        padding: 2,
                    },
                ],
            },
        ],

        signals: [
            {
                name: "width",
                value: "",
                on: [
                    {
                        events: {
                            source: "window",
                            type: "resize",
                            debounce: 25,
                        },
                        update: "containerSize()[0]",
                    },
                ],
            },
            {
                name: "height",
                value: "",
                on: [
                    {
                        events: {
                            source: "window",
                            type: "resize",
                            debounce: 25,
                        },
                        update: "containerSize()[1]",
                    },
                ],
            },
        ],
    };

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => {
            viewWordCloud = res.view;
        })
        .catch(console.error);
}
