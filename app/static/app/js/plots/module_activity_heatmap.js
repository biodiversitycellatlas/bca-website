/**
 * Gene module activity heatmap.
 */

/* global vegaEmbed */

export let viewActivityHeatmap;

/**
 * Render heatmap of gene expression for a given dataset.
 *
 * @param {string} id - DOM element ID where the heatmap will be embedded.
 * @param {Array} data - Array of objects with metacell and gene module eigenvalues.
 * @param {Array} clip - Array with min and max scores to clip eigenvalues (default:
 *   [-0.1, 0.2]). Use null to avoid limits, such as [null, null] or [null, 0.4].
 */
export function createActivityHeatmap(id, data, clip = [-0.1, 0.2]) {
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        height: "container",
        data: { name: "exprData", values: data },
        transform: [
            { calculate: "toNumber(datum.metacell_name)", as: "metacell_name" },
            {
                joinaggregate: [
                    { op: "distinct", field: "module", as: "module_count" },
                    {
                        op: "distinct",
                        field: "metacell_name",
                        as: "metacell_count",
                    },
                ],
            },
        ],
        vconcat: [
            {
                width: "container",
                mark: "rect",
                encoding: {
                    x: {
                        field: "metacell_name",
                        axis: {
                            labels: false,
                            ticks: false,
                            orient: "top",
                            title: {
                                expr: "data('data_0')[0].metacell_count + ' Metacells'"
                            },
                        },
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
                                field: "module",
                                sort: { field: "index" },
                                axis: {
                                    labels: false,
                                    ticks: false,
                                    title: {
                                        expr: "data('data_0')[0].module_count + ' Gene Modules'"
                                    },
                                },
                            },
                            color: {
                                field: "eigenvalue",
                                type: "quantitative",
                                title: "Eigenvalues",
                                scale: {
                                    domainMin: clip[0],
                                    domainMax: clip[1],
                                    clamp: true,
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
                        axis: {
                            labels: false,
                            ticks: false,
                            title: {
                                expr: "data('data_0')[0].metacell_count + ' Metacells'"
                            },
                        },
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
            viewActivityHeatmap = res.view;
        })
        .catch(console.error);
}
