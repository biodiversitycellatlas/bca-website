/* global vegaEmbed */

export let viewStats;

function prepareStatsSpecPerParam(param, label = param, counts = true) {
    var plot = [
        {
            transform: [{ density: param, counts: counts }],
            encoding: {
                x: {
                    field: "value",
                    type: "quantitative",
                    title: "",
                    axis: { format: "s" },
                },
                y: {
                    field: "density",
                    type: "quantitative",
                    title: "Density",
                },
            },
            layer: [
                {
                    // Density plot
                    mark: {
                        type: "area",
                        fill: "gray",
                        opacity: 0.1,
                        stroke: "gray",
                        strokeWidth: 2,
                    },
                    params: [
                        {
                            name: "brush",
                            select: { type: "interval", encodings: ["x"] },
                            bind: "scales",
                        },
                    ],
                },
                {
                    // Highlight point on mouse hover
                    params: [
                        {
                            name: "hover",
                            select: {
                                type: "point",
                                fields: ["value"],
                                nearest: true,
                                on: "pointerover",
                                clear: "pointerout",
                            },
                        },
                    ],
                    mark: {
                        type: "point",
                        fill: "gray",
                        opacity: 0.1,
                        stroke: "gray",
                        strokeWidth: 2,
                    },
                    encoding: {
                        opacity: {
                            condition: {
                                param: "hover",
                                empty: false,
                                value: 1,
                            },
                            value: 0,
                        },
                    },
                },
                {
                    // Add rule on mouse hover
                    mark: "rule",
                    encoding: {
                        y: null,
                        opacity: {
                            condition: {
                                value: 0.3,
                                param: "hover",
                                empty: false,
                            },
                            value: 0,
                        },
                    },
                },
                {
                    // Add text on mouse hover
                    mark: { type: "text", align: "left", dx: 10 },
                    encoding: {
                        text: { type: "quantitative", field: "value" },
                        opacity: {
                            condition: {
                                value: 1,
                                param: "hover",
                                empty: false,
                            },
                            value: 0,
                        },
                    },
                },
            ],
        },
        {
            // Boxplot
            mark: { type: "boxplot", color: "gray" },
            encoding: {
                x: {
                    field: param,
                    title: label,
                    type: "quantitative",
                    scale: { zero: false },
                },
                y: { value: 170 },
            },
        },
        {
            // Rug plot using circles
            mark: {
                type: "circle",
                size: 150,
                color: "orange",
                opacity: 0.8,
                stroke: "white",
                strokeWidth: 1,
                tooltip: { content: "data" },
            },
            //"transform": [{"calculate": "random()", "as": "random"}],
            encoding: {
                x: { field: param, type: "quantitative" },
                y: { value: 190 },
                color: {
                    field: "metacell_type",
                    scale: { range: { field: "metacell_color" } },
                    title: "Cell type",
                    legend: false,
                },
            },
        },
    ];
    return plot;
}

export function createStatsPlot(id, data, param, title, label=param, counts=true) {
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        title: { text: title },
        data: { name: "data", values: data },
        width: "container",
        layer: prepareStatsSpecPerParam(param, label, counts),
        config: {
            style: { cell: { stroke: "transparent" } },
            axis: { grid: false },
        },
    };
    vegaEmbed(id, chart)
        .then((res) => {
            viewStats = res.view;
        })
        .catch(console.error);
}
