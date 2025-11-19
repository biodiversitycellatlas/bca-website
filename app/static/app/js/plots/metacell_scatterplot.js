/**
 * Metacell projection scatterplot.
 */

/* global vegaEmbed */

export let viewMetacellProjection;

/**
 * Generate color scale based on data type and color.
 *
 * @param {Array} data - Array of objects with 'type' and 'color' properties.
 * @returns {Object} scale - Object with 'domain' (unique types) and 'range' (corresponding colors).
 */
function generateColorScale(data) {
    const colors = {};
    data.forEach(({ type, color }) => (colors[type] = color));

    const sorted_colors = {};
    Object.keys(colors)
        .sort()
        .forEach((key) => {
            sorted_colors[key] = colors[key];
        });

    const scale = {
        domain: Object.keys(sorted_colors),
        range: Object.values(sorted_colors),
    };
    return scale;
}

/**
 * Create metacell projection chart.
 *
 * @param {string} id - CSS selector for target element.
 * @param {string} species - Species name.
 * @param {Object} data - Object with `sc_data`, `mc_data`, `mc_links`.
 * @param {boolean} [color_by_metacell_type=true] - Color points by metacell type.
 * @param {string|null} [gene=null] - Optional gene name for subtitle.
 */
export function createMetacellProjection(
    id,
    species,
    data,
    color_by_metacell_type = true,
    gene = null,
) {
    var metacellColorScale = generateColorScale(data["mc_data"]);
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        title: {
            text: {
                expr: "data('sc_data').length + ' cells, ' + data('mc_data').length + ' metacells'",
            },
            subtitle: gene !== null ? gene + " expression" : null,
            fontWeight: "normal",
            anchor: "start",
        },
        width: "container",
        height: "container",
        params: [
            { name: "showCells", bind: { element: "#projection-cells" } },
            {
                name: "showMetacells",
                bind: { element: "#projection-metacells" },
            },
            { name: "showLabels", bind: { element: "#projection-labels" } },
            { name: "showLinks", bind: { element: "#projection-links" } },
        ],
        layer: [
            {
                data: { name: "sc_data", values: data["sc_data"] },
                mark: {
                    type: "circle",
                    tooltip: { encoding: "data" },
                    invalid: null,
                },

                // Avoid drawing cells with null coordinates
                transform: [{ filter: "datum.x != null && datum.y != null" }],

                // Avoid this transform for cells: this changes axis limits
                // "transform": [ { "filter": "showCells == 'true'" } ],

                params: [{ name: "brush", select: { type: "interval" } }],
                encoding: {
                    x: { field: "x", type: "quantitative" },
                    y: { field: "y", type: "quantitative" },
                    color: {
                        condition: {
                            test: "datum.umifrac == null",
                            value: "#F1F7FE",
                        },
                        title: "UMI/10K",
                        field: "umifrac",
                        type: "quantitative",
                        scale: { scheme: "magma", reverse: true },
                    },
                    opacity: {
                        condition: {
                            test: "showCells == 'true'",
                            value: 0.7,
                            type: "nominal",
                        },
                        value: 0,
                    },
                    tooltip: {
                        condition: {
                            test: "showCells == 'false'",
                            value: null,
                        },
                    },
                },
            },
            {
                data: { name: "mc_links", values: data["mc_links"] },
                mark: "rule",
                transform: [{ filter: "showLinks == 'true'" }],
                encoding: {
                    x: { field: "metacell_x", type: "quantitative" },
                    x2: { field: "metacell2_x", type: "quantitative" },
                    y: { field: "metacell_y", type: "quantitative" },
                    y2: { field: "metacell2_y", type: "quantitative" },
                    color: { value: "#B7B7B7" },
                },
            },
            {
                data: { name: "mc_data", values: data["mc_data"] },
                mark: {
                    type: "circle",
                    stroke: "white",
                    strokeWidth: 1,
                    tooltip: { encoding: "data" },
                    invalid: null,
                },
                transform: [
                    {
                        calculate:
                            "datum.fold_change == null ? null : log(datum.fold_change) / log(2)",
                        as: "log2_fold_change",
                    },
                    { filter: "showMetacells == 'true'" },
                ],
                encoding: {
                    x: { field: "x", type: "quantitative" },
                    y: { field: "y", type: "quantitative" },
                    size: { value: 400 },
                    fill: {
                        condition: {
                            test: "datum.log2_fold_change == null",
                            value: "#F1F7FE",
                        },
                        title: "Log\u2082 FC",
                        field: "log2_fold_change",
                        type: "quantitative",
                        scale: { scheme: "magma", reverse: true },
                    },
                    opacity: { value: 0.7 },
                },
            },
            {
                data: { name: "mc_data" },
                mark: "text",
                transform: [{ filter: "showLabels == 'true'" }],
                encoding: {
                    x: { field: "x", type: "quantitative" },
                    y: { field: "y", type: "quantitative" },
                    text: { field: "name" },
                    opacity: { value: 0.7 },
                },
            },
        ],
        config: {
            style: { cell: { stroke: "transparent" } },
            axis: {
                domain: false,
                grid: false,
                ticks: false,
                labels: false,
                title: null,
            },
        },
    };

    // Colour by metacell_type
    if (color_by_metacell_type) {
        // The vega-lite conditions do not support updating the legend when
        // changing the field/type used for colouring
        chart.layer[0].encoding.color = {
            field: "metacell_type",
            scale: metacellColorScale,
            title: "Cell type",
        };

        delete chart.layer[2].encoding.fill;
        chart.layer[2].encoding.color = {
            field: "type",
            scale: metacellColorScale,
            title: "Cell type",
        };
    }

    vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => {
            viewMetacellProjection = res.view;
        })
        .catch(console.error);
}
