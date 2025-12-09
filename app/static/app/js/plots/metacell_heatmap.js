/**
 * Heatmaps.
 */

/* global vegaEmbed */

export let viewExpressionHeatmap;
export let viewActivityHeatmap;

export const COLOR_SCALE = ["#F2F2F2", "#FFA500", "#EE4000", "#520c52"];

/**
 * Build a rug plot showing metacell group colors (placed above/below heatmap)
 *
 * @param {string} [orient="top"] - Position of the rug plot ("top" or "bottom").
 *
 * @returns {Object} Vega-Lite specification for the rug plot.
 */
function createMetacellRugPlot(orient = "top") {
    return {
        width: "container",
        mark: "rect",
        encoding: {
            x: {
                field: "metacell_name",
                axis: {
                    labels: false,
                    ticks: false,
                    orient: orient,
                    title: {
                        expr: "data('data_0')[0].metacell_count + ' Metacells'",
                    },
                },
            },
            color: {
                field: "metacell_color",
                legend: false,
                scale: { range: { field: "metacell_color" } },
            },
            tooltip: [{ field: "metacell_name" }, { field: "metacell_type" }],
        },
    };
}

/**
 * Build a heatmap of values across metacells.
 *
 * @param {string} id - DOM element ID where the chart will be rendered.
 * @param {Array} data - Input records containing metacell info and data values.
 * @param {string} yField - Field used for the heatmap’s vertical axis.
 * @param {string} yLabel - Label for the vertical axis.
 * @param {string} valueField - Field containing data values to color the heatmap.
 * @param {string} valueLabel - Label for the color legend.
 * @param {string} [boundaryColor="black"] - Color for metacell boundary lines.
 * @param {Array} [clip=[null, null]] - Min/max clipping range for color scaling.
 *
 * @returns {Object} Vega-Lite specification for the heatmap.
 */
function createMetacellHeatmap(
    id,
    data,
    yField,
    yLabel,
    valueField,
    valueLabel,
    boundaryColor = "black",
    clip = [null, null],
) {
    var metacellBoundaryLines = {
        mark: "rule",
        transform: [
            // Filter first value for each metacell type
            {
                window: [{ op: "row_number", as: "rn" }],
                groupby: ["metacell_type"],
                sort: [{ field: "metacell_name", order: "ascending" }],
            },
            { filter: "datum.rn === 1" },

            // Discard first value (overlaps the Y-axis grid line)
            {
                window: [{ op: "row_number", as: "rn_all" }],
                sort: [{ field: "metacell_name", order: "ascending" }],
            },
            { filter: "datum.rn_all > 1" },
        ],
        encoding: {
            // Position first mark to the left
            x: { field: "metacell_name", bandPosition: 0 },
            color: { value: boundaryColor },
            strokeWidth: { value: 0.5 },
        },
    };

    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        height: "container",
        data: { name: "exprData", values: data },
        transform: [
            { calculate: "toNumber(datum.metacell_name)", as: "metacell_name" },
            {
                joinaggregate: [
                    { op: "distinct", field: yField, as: "y_count" },
                    {
                        op: "distinct",
                        field: "metacell_name",
                        as: "metacell_count",
                    },
                ],
            },
        ],
        vconcat: [
            createMetacellRugPlot(),
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
                                field: yField,
                                axis: {
                                    labels: true,
                                    labelExpr:
                                        "data('data_0')[0].y_count < 80 ? datum.label : ''",
                                    ticks: false,
                                    title: {
                                        expr: `data('data_0')[0].y_count + ' ${yLabel}'`,
                                    },
                                },
                                sort: { field: "index" },
                            },
                            color: {
                                field: valueField,
                                type: "quantitative",
                                axis: {
                                    labels: false,
                                    ticks: false,
                                    title: valueLabel,
                                },
                                scale: {
                                    domainMin: clip[0],
                                    domainMax: clip[1],
                                    clamp: true,
                                    range: COLOR_SCALE,
                                },
                            },
                        },
                    },
                    metacellBoundaryLines,
                ],
            },
            createMetacellRugPlot("bottom"),
        ],
        config: { view: { stroke: "transparent" } },
    };
    return chart;
}

/**
 * Render heatmap of gene expression for a given species and dataset.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {Array} data - Array of objects containing metacell and gene expression data.
 * @param {Array} clip - Array with min and max scores to clip gene expression.
 */
export function createExpressionHeatmap(id, data, clip = [null, null]) {
    let chart = createMetacellHeatmap(
        id,
        data,
        "gene_name",
        "Genes",
        "log2_fold_change",
        "Log\u2082 FC",
        "gray",
        clip,
    );

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => (viewExpressionHeatmap = res.view))
        .catch(console.error);
}

/**
 * Render heatmap of gene expression for a given dataset.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {Array} data - Array of objects with metacell and gene module eigenvalues.
 * @param {Array} clip - Array with min and max scores to clip eigenvalues.
 */
export function createActivityHeatmap(id, data, clip = [-0.1, 0.2]) {
    let chart = createMetacellHeatmap(
        id,
        data,
        "module",
        "Gene Modules",
        "eigenvalue",
        "Eigenvalues",
        "black",
        clip,
    );

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => (viewActivityHeatmap = res.view))
        .catch(console.error);
}
