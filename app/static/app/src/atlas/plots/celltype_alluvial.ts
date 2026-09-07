/**
 * Cell-type similarity alluvial plot
 */

import vegaEmbed from "vega-embed";

/**
 * Renders an alluvial diagram to compare similarity scores between metacell types
 * from two species
 *
 * Based on https://github.com/PBI-David/Deneb-Showcase
 *
 * @param {string} id - CSS selector of the target HTML element
 * @param {string} dataset_label - Label to annotate the first dataset
 * @param {string} dataset2_label - Label to annotate the second dataset
 * @param {Array<Object>} data - Array of objects containing metacell type pairs and scores
 * @param {string} scoreField - Field name for the score (e.g. 'samap_score', 'pesci_score')
 * @param {string} metricLabel - Display label for the metric (e.g. 'SAMap', 'Pesci')
 */
export function createCellTypeAlluvial(id, data, dataset_label, dataset2_label, scoreField = "samap_score", metricLabel = "SAMap") {
    // If direction of datasets is reversed, switch labels
    const normalize = (str) => str.toLowerCase().replace(/[^a-z]/g, "");
    if (
        normalize(data[0].dataset) == normalize(dataset2_label) &&
        normalize(data[0].dataset2) == normalize(dataset_label)
    ) {
        [dataset_label, dataset2_label] = [dataset2_label, dataset_label];
    }

    const genePairCountField = scoreField
        .replace(/_score$/, "_gene_pair_count")
        .replace(/_1to2$/, "_gene_pair_count");

    const chart = {
        $schema: "https://vega.github.io/schema/vega/v6.json",
        autosize: {
            type: "fit",
            contains: "padding",
        },
        signals: [
            {
                name: "gap",
                value: 3,
                description: "Gap between rectangles",
            },
            {
                name: "textPadding",
                value: 8,
                description: "Text padding",
            },
            {
                name: "innerPadding",
                value: 0.9,
                description: "Inner padding",
            },
            {
                name: "width",
                init: "isFinite(containerSize()[0]) ? containerSize()[0] : 200",
                on: [
                    {
                        update: "isFinite(containerSize()[0]) ? containerSize()[0] : 200",
                        events: "window:resize",
                    },
                ],
            },
            {
                name: "height",
                init: "isFinite(containerSize()[1]) ? containerSize()[1] : 200",
                on: [
                    {
                        update: "isFinite(containerSize()[1]) ? containerSize()[1] : 200",
                        events: "window:resize",
                    },
                ],
            },
        ],
        data: [
            {
                name: "input",
                values: data,
            },
            {
                name: "input_id",
                source: "input",
                transform: [
                    {
                        type: "formula",
                        as: "id",
                        expr: "[ datum.dataset + '__' + datum.metacell_type, datum.dataset2 + '__' + datum.metacell2_type]",
                    },
                    {
                        type: "formula",
                        as: "metacell_type_id",
                        expr: "datum.dataset + '__' + datum.metacell_type",
                    },
                    {
                        type: "formula",
                        as: "metacell2_type_id",
                        expr: "datum.dataset2 + '__' + datum.metacell2_type",
                    },
                ],
            },
            {
                name: "stacks",
                source: "input_id",
                transform: [
                    {
                        type: "formula",
                        as: "end",
                        expr: "['metacell_type', 'metacell2_type']",
                    },
                    {
                        type: "formula",
                        as: "name",
                        expr: "[ datum.metacell_type, datum.metacell2_type]",
                    },
                    {
                        type: "flatten",
                        fields: ["end", "name", "id"],
                    },
                    {
                        type: "formula",
                        as: "color",
                        expr: "datum.end === 'metacell_type' ? datum.metacell_color : datum.metacell2_color",
                    },
                    {
                        type: "aggregate",
                        fields: [scoreField],
                        groupby: ["end", "name", "id", "color"],
                        ops: ["sum"],
                        as: [scoreField],
                    },
                    {
                        type: "formula",
                        as: "stack",
                        expr: "datum.end === 'metacell_type' ? 1 : 2",
                    },
                ],
            },
            {
                name: "maxScore",
                source: ["stacks"],
                transform: [
                    {
                        type: "aggregate",
                        fields: [scoreField],
                        groupby: ["stack"],
                        ops: ["sum"],
                        as: [scoreField],
                    },
                ],
            },
            {
                name: "plottedStacks",
                source: ["stacks"],
                transform: [
                    {
                        type: "formula",
                        as: "spacer",
                        expr: `(data('maxScore')[0].${scoreField}/100) * gap`,
                    },
                    {
                        type: "formula",
                        as: "type",
                        expr: "['data', 'spacer']",
                    },
                    {
                        type: "formula",
                        as: "spacedScore",
                        expr: `[datum.${scoreField}, datum.spacer]`,
                    },
                    {
                        type: "flatten",
                        fields: ["type", "spacedScore"],
                    },
                    {
                        type: "stack",
                        groupby: ["stack"],
                        field: "spacedScore",
                        offset: "center",
                    },
                    {
                        type: "formula",
                        expr: `datum.${scoreField}/2 + datum.y0 - 8`,
                        as: "yc",
                    },
                ],
            },
            {
                name: "finalTable",
                source: "plottedStacks",
                transform: [{ type: "filter", expr: "datum.type == 'data'" }],
            },
            {
                name: "linkTable",
                source: "input_id",
                transform: [
                    {
                        type: "lookup",
                        from: "finalTable",
                        key: "id",
                        values: ["y0", "stack"],
                        fields: ["metacell_type_id", "metacell2_type_id"],
                        as: [
                            "metacell_typeStacky0",
                            "metacell_typeStack",
                            "metacell2_typeStacky0",
                            "metacell2_typeStack",
                        ],
                    },
                    {
                        type: "stack",
                        groupby: ["metacell_type"],
                        field: scoreField,
                        as: ["syi0", "syi1"],
                    },
                    {
                        type: "formula",
                        expr: `((datum.${scoreField})/2) + datum.syi0 + datum.metacell_typeStacky0`,
                        as: "syc",
                    },
                    {
                        type: "stack",
                        groupby: ["metacell2_type"],
                        field: scoreField,
                        as: ["dyi0", "dyi1"],
                    },
                    {
                        type: "formula",
                        expr: `((datum.${scoreField})/2) + datum.dyi0 + datum.metacell2_typeStacky0`,
                        as: "dyc",
                    },
                    {
                        type: "linkpath",
                        orient: "horizontal",
                        shape: "diagonal",
                        sourceY: { expr: "scale('y', datum.syc)" },
                        sourceX: { expr: "scale('x', 1) + bandwidth('x')" },
                        targetY: { expr: "scale('y', datum.dyc)" },
                        targetX: { expr: "scale('x', 2)" },
                    },
                    {
                        type: "formula",
                        expr: `range('y')[0] - scale('y', datum.${scoreField})`,
                        as: "strokeWidth",
                    },
                ],
            },
        ],
        scales: [
            {
                name: "x",
                type: "band",
                range: "width",
                domain: [1, 2],
                paddingInner: { signal: "innerPadding" },
            },
            {
                name: "y",
                range: "height",
                domain: { data: "finalTable", field: "y1" },
            },
        ],
        marks: [
            {
                name: "nodes",
                type: "rect",
                from: { data: "finalTable" },
                encode: {
                    update: {
                        x: { scale: "x", field: "stack" },
                        width: { scale: "x", band: 1 },
                        y: { scale: "y", field: "y0" },
                        y2: { scale: "y", field: "y1" },
                        fill: { signal: "datum.color" },
                        fillOpacity: { value: 0.75 },
                        stroke: { signal: "datum.color" },
                    },
                    hover: {
                        fillOpacity: { value: 1 },
                    },
                },
            },
            {
                name: "links",
                type: "path",
                from: { data: "linkTable" },
                clip: true,
                encode: {
                    update: {
                        strokeWidth: { field: "strokeWidth" },
                        path: { field: "path" },
                        strokeOpacity: { signal: "0.3" },
                        stroke: { signal: "datum.metacell2_color" },
                        cursor: { value: "pointer" },
                    },
                    hover: {
                        strokeOpacity: { value: 1 },
                        tooltip: {
                            signal: `{'Cell type ←': datum.metacell_type, 'Cell type →': datum.metacell2_type, '${metricLabel}': format(datum.${scoreField}, '.2f') + '%', 'Gene pairs': datum.${genePairCountField}}`,
                        },
                    },
                },
            },
            {
                type: "group",
                zindex: 1,
                clip: false,
                marks: [
                    {
                        type: "text",
                        from: { data: "finalTable" },
                        encode: {
                            update: {
                                x: {
                                    scale: "x",
                                    field: "stack",
                                    offset: {
                                        signal: "datum.stack == 1 ? -textPadding : bandwidth('x') + textPadding",
                                    },
                                },
                                text: { field: "name" },
                                align: {
                                    signal: "datum.stack == 1 ? 'right' : 'left'",
                                },
                                yc: { scale: "y", signal: "datum.yc" },
                            },
                        },
                    },
                    {
                        type: "text",
                        encode: {
                            update: {
                                x: { scale: "x", value: 1, band: 0.5 },
                                y: { value: -15 },
                                text: { value: dataset_label },
                                align: { value: "center" },
                                fontSize: { value: 14 },
                                fontStyle: { value: "italic" },
                            },
                        },
                    },
                    {
                        type: "text",
                        encode: {
                            update: {
                                x: { scale: "x", value: 2, band: 0.5 },
                                y: { value: -15 },
                                text: { value: dataset2_label },
                                align: { value: "center" },
                                fontSize: { value: 14 },
                                fontStyle: { value: "italic" },
                            },
                        },
                    },
                ],
            },
        ],
    };

    return vegaEmbed(id, chart, { renderer: "canvas" })
        .then((res) => res.view)
        .catch((error) => {
            console.error(error);
            throw error;
        });
}
