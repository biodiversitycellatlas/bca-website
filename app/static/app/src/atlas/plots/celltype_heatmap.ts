/**
 * Cell-type similarity heatmap
 */

import vegaEmbed from "vega-embed";

/**
 * Renders a heatmap to compare similarity scores between metacell types from
 * different species
 *
 * @param {string} id - CSS selector of the target HTML element
 * @param {string} dataset_label - Label to annotate the first dataset
 * @param {string} dataset2_label - Label to annotate the second dataset
 * @param {Array<Object>} data - Array of objects containing metacell type pairs and scores
 * @param {string} scoreField - Field name for the score (e.g. 'samap_score', 'pesci_score', 'aucell_1to2')
 * @param {string} metricLabel - Display label for the metric (e.g. 'SAMap', 'Pesci', 'AUCell')
 */
export function createCellTypeHeatmap(id, data, dataset_label, dataset2_label, scoreField = "samap_score", metricLabel = "SAMap") {
    // If direction of datasets is reversed, switch labels
    const normalize = (str) => str.toLowerCase().replace(/[^a-z]/g, "");
    if (
        normalize(data[0].dataset) == normalize(dataset2_label) &&
        normalize(data[0].dataset2) == normalize(dataset_label)
    ) {
        [dataset_label, dataset2_label] = [dataset2_label, dataset_label];
    }

    const scoreFormatted = `${scoreField}_formatted`;
    const genePairCountField = scoreField
        .replace(/_score$/, "_gene_pair_count")
        .replace(/_1to2$/, "_gene_pair_count");

    const chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        height: "container",
        data: { name: "exprData", values: data },
        transform: [
            {
                calculate: `format(datum.${scoreField}, '.2f') + '%'`,
                as: scoreFormatted,
            },
        ],
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
                            tooltip: [{ field: "metacell_type" }],
                        },
                    },
                    {
                        width: "container",
                        height: 500,
                        mark: {
                            type: "rect",
                            cursor: "pointer",
                        },
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
                                field: scoreField,
                                type: "quantitative",
                                title: metricLabel,
                                legend: {
                                    labelExpr: "datum.value + '%'",
                                },
                                scale: {
                                    domain: [0, 100],
                                    range: [
                                        "#F2F2F2",
                                        "#FFA500",
                                        "#EE4000",
                                        "#520c52",
                                    ],
                                },
                            },
                            tooltip: [
                                {
                                    field: "metacell_type",
                                    title: "Cell type ←",
                                },
                                {
                                    field: "metacell2_type",
                                    title: "Cell type →",
                                },
                                {
                                    field: scoreFormatted,
                                    title: metricLabel,
                                },
                                {
                                    field: genePairCountField,
                                    title: "Gene pairs",
                                },
                            ],
                        },
                    },
                ],
            },
            {
                hconcat: [
                    {
                        width: 21,
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

    return vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => res.view)
        .catch((error) => {
            console.error(error);
            throw error;
        });
}
