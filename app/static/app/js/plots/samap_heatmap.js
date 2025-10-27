/**
 * SAMap sankey plot
 */

export let viewSAMapHeatmap;

/* global vegaEmbed */

/**
 * Renders a heatmap to compare SAMap scores between metacell types from
 * different species
 *
 * @param {string} id - CSS selector of the target HTML element
 * @param {string} dataset_label - Label to annotate the first dataset
 * @param {string} dataset2_label - Label to annotate the second dataset
 * @param {Array<Object>} data - Array of objects containing:
 *   - dataset: slug of the first dataset
 *   - metacell_type: cell type from the first dataset
 *   - metacell_color: color for metacell_type
 *   - dataset2: slug of the second dataset
 *   - metacell2_type: cell type from the second dataset
 *   - metacell2_color: color for metacell2_type
 *   - samap: SAMap score between the two metacell types
 */
export function createSAMapHeatmap(id, data, dataset_label, dataset2_label) {
    // If direction of datasets is reversed, switch labels
    const normalize = (str) => str.toLowerCase().replace(/[^a-z]/g, "");
    if (
        normalize(data[0].dataset) == normalize(dataset2_label) &&
        normalize(data[0].dataset2) == normalize(dataset_label)
    ) {
        [dataset_label, dataset2_label] = [dataset2_label, dataset_label];
    }

    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        height: "container",
        data: { name: "exprData", values: data },
        vconcat: [
            {
                hconcat: [
                    {
                        height: 500,
                        mark: "rect",
                        encoding: {
                            y: {
                                field: "metacell_type",
                                axis: { labels: false, ticks: false },
                                sort: { field: "index" },
                                title: "Metacell types from " + dataset_label,
                            },
                            color: {
                                field: "metacell_color",
                                legend: false,
                                scale: { range: { field: "metacell_color" } },
                            },
                            tooltip: [
                                { field: "metacell_type" },
                                { field: "metacell_color" },
                            ],
                        },
                    },
                    {
                        width: "container",
                        height: 500,
                        mark: { type: "rect", tooltip: { content: "data" } },
                        encoding: {
                            x: {
                                field: "metacell2_type",
                                axis: { labels: false, ticks: false },
                                sort: { field: "index" },
                                title: "",
                            },
                            y: {
                                field: "metacell_type",
                                axis: { labels: false, ticks: false },
                                sort: { field: "index" },
                                title: "",
                            },
                            color: {
                                field: "samap",
                                type: "quantitative",
                                title: "SAMap scores",
                                scale: {
                                    range: [
                                        "#F2F2F2",
                                        "#FFA500",
                                        "#EE4000",
                                        "#520c52",
                                    ],
                                },
                            },
                        },
                    },
                ],
            },
            {
                hconcat: [
                    {
                        width: 36,
                        mark: { type: "rect", opacity: 0 },
                    },
                    {
                        width: "container",
                        mark: "rect",
                        encoding: {
                            x: {
                                field: "metacell2_type",
                                axis: { labels: false, ticks: false },
                                sort: { field: "index" },
                                title: "Metacell types from " + dataset2_label,
                            },
                            color: {
                                field: "metacell2_color",
                                legend: false,
                                scale: { range: { field: "metacell2_color" } },
                            },
                            tooltip: [{ field: "metacell2_type" }],
                        },
                    },
                ],
            },
        ],
        config: { view: { stroke: "transparent" } },
    };

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => {
            viewSAMapHeatmap = res.view;
        })
        .catch(console.error);
}
