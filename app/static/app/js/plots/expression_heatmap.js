/**
 * Gene expression heatmaps.
 */

/* global vegaEmbed */

export let viewExpressionHeatmap;

/**
 * Render heatmap of gene expression for a given species and dataset.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {string} species - Species name (used for metadata or future extensions).
 * @param {Array} data - Array of objects containing metacell and gene expression data.
 */
export function createExpressionHeatmap(id, species, data) {
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        height: "container",
        data: { name: "exprData", values: data },
        transform: [
            { calculate: "toNumber(datum.metacell_name)", as: "metacell_name" },
            {
                joinaggregate: [
                    { op: "distinct", field: "gene_name", as: "gene_count" },
                    {
                        op: "distinct",
                        field: "metacell_name",
                        as: "metacell_count",
                    },
                ],
            },
        ],
        params: [
            {
                name: "title",
                expr: "data('data_0')[0].gene_count + ' genes, ' + data('data_0')[0].metacell_count + ' metacells'",
            },
        ],
        title: {
            text: { expr: "title" },
            fontWeight: "normal",
            anchor: "start",
        },
        vconcat: [
            {
                width: "container",
                mark: "rect",
                encoding: {
                    x: {
                        field: "metacell_name",
                        axis: { labels: false, ticks: false },
                        title: "Metacells",
                    },
                    color: {
                        field: "metacell_color",
                        legend: false,
                        scale: { range: { field: "metacell_color" } },
                    },
                    tooltip: [
                        { field: "metacell_name" },
                        { field: "metacell_type" },
                        { field: "metacell_color" },
                    ],
                },
            },
            {
                width: "container",
                height: 500,
                layer: [
                    {
                        mark: { type: "rect", tooltip: { content: "data" } },
                        encoding: {
                            x: {
                                field: "metacell_name",
                                axis: { labels: false, ticks: false },
                                title: "",
                            },
                            y: {
                                field: "gene_name",
                                axis: { labels: false, ticks: false },
                                sort: { field: "index" },
                                title: "Genes",
                            },
                            color: {
                                field: "log2_fold_change",
                                type: "quantitative",
                                title: "Log\u2082 FC",
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
                    {
                        mark: "rule",
                        transform: [
                            // Filter first value for each metacell type
                            {
                                window: [{ op: "row_number", as: "rn" }],
                                groupby: ["metacell_type"],
                                sort: [
                                    {
                                        field: "metacell_name",
                                        order: "ascending",
                                    },
                                ],
                            },
                            {
                                filter: "datum.rn === 1",
                            },

                            // Discard first value (overlaps the Y-axis grid line)
                            {
                                window: [{ op: "row_number", as: "rn_all" }],
                                sort: [
                                    {
                                        field: "metacell_name",
                                        order: "ascending",
                                    },
                                ],
                            },
                            {
                                filter: "datum.rn_all > 1",
                            },
                        ],
                        encoding: {
                            // Position first mark to the left
                            x: { field: "metacell_name", bandPosition: 0 },
                            color: { value: "gray" },
                            strokeWidth: { value: 0.5 },
                        },
                    },
                ],
            },
            {
                width: "container",
                mark: "rect",
                encoding: {
                    x: {
                        field: "metacell_name",
                        axis: { labels: false, ticks: false },
                        title: "Metacells",
                    },
                    color: {
                        field: "metacell_color",
                        legend: false,
                        scale: { range: { field: "metacell_color" } },
                    },
                    tooltip: [
                        { field: "metacell_name" },
                        { field: "metacell_type" },
                    ],
                },
            },
        ],
        config: { view: { stroke: "transparent" } },
    };
    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => {
            viewExpressionHeatmap = res.view;
        })
        .catch(console.error);
}
