/**
 * Gene expression visualizations.
 */

/* global vegaEmbed */

import { escapeString } from "../utils/utils.js";

/**
 * Render bubble plot showing expression levels of a single gene across metacells.
 *
 * @param {string} id - DOM element ID where the plot will be embedded.
 * @param {string} gene - Name of the gene to visualize.
 * @param {Array} data - Array of objects containing metacell expression data.
 */
export function createExpressionBubblePlot(id, gene, data) {
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        //"title": { "text": gene, "fontWeight": "normal", "anchor": "start" },
        transform: [
            { calculate: "toNumber(datum.metacell_name)", as: "metacell_name" },
            { calculate: "datum.umifrac * 10", as: "umifrac" },
            { fold: ["umifrac", "fold_change"] },
        ],
        data: { name: "gene_data", values: data },
        width: "container",
        mark: { type: "circle", tooltip: { content: "data" } },
        encoding: {
            x: {
                field: "metacell_name",
                type: "quantitative",
                title: "Metacell",
                axis: {
                    labels: false,
                    ticks: false,
                },
                scale: { nice: false },
            },
            y: { field: "key", title: "" },
            size: {
                field: "value",
                type: "quantitative",
                impute: { value: 0 },
                legend: null,
            },
            color: {
                field: "metacell_type",
                scale: { range: { field: "metacell_color" } },
                legend: null,
                // "legend": { "orient": "bottom", "direction": "horizontal", "columns": 4 }
            },
            tooltip: [
                { field: "metacell_name" },
                { field: "metacell_type" },
                { field: "umi_raw" },
                { field: "umifrac" },
                { field: "fold_change" },
            ],
        },
        params: [
            // Pan and zoom plot
            {
                name: "brush",
                select: { type: "interval", encodings: ["x"] },
                bind: "scales",
            },
        ],
        scale: {
            type: "ordinal",
            nice: false,
            tickStep: 1,
        },
    };
    vegaEmbed(id, chart).catch(console.error);
}

/**
 * Render comparison scatter plot of two genes' expression across metacells
 * with regression line and correlation stats.
 *
 * @param {string} id - DOM element ID where the plot will be embedded.
 * @param {string} gene - Name of the first gene.
 * @param {string} gene2 - Name of the second gene.
 * @param {Array} data - Array of objects containing metacell expression data.
 * @param {Object} stats - Object containing correlation statistics (pearson, spearman).
 */
export function createExpressionComparisonPlot(id, gene, gene2, data, stats) {
    let escapedGene = escapeString(gene),
        escapedGene2 = escapeString(gene2);

    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v6.json",
        title: {
            text: [`Pearson: ${stats.pearson}`, `Spearman: ${stats.spearman}`],
            fontWeight: "normal",
            anchor: "end",
        },
        transform: [
            { calculate: "toNumber(datum.metacell_name)", as: "metacell_name" },
            { calculate: "datum.umifrac * 10", as: "umifrac" },
            {
                pivot: "gene_name",
                groupby: ["metacell_name", "metacell_type", "metacell_color"],
                value: "fold_change",
            },
            {
                joinaggregate: [
                    { op: "min", field: escapedGene, as: "xMin" },
                    { op: "max", field: escapedGene, as: "xMax" },
                    { op: "min", field: escapedGene2, as: "yMin" },
                    { op: "max", field: escapedGene2, as: "yMax" },
                ],
            },
            { calculate: "min(datum.xMin, datum.yMin)", as: "min" },
            { calculate: "max(datum.xMax, datum.yMax)", as: "max" },
        ],
        data: { name: "data", values: data },
        width: "container",
        encoding: {
            x: {
                field: escapedGene,
                type: "quantitative",
                title: gene + " fold-change",
                scale: {
                    domain: {
                        expr: "[data('data_0')[0]['min'], data('data_0')[0]['max']]",
                    },
                },
            },
            y: {
                field: escapedGene2,
                type: "quantitative",
                title: gene2 + " fold-change",
                scale: {
                    domain: {
                        expr: "[data('data_0')[0]['min'], data('data_0')[0]['max']]",
                    },
                },
            },
        },
        layer: [
            {
                // Add regression line
                mark: {
                    type: "line",
                    color: "gray",
                    strokeWidth: 1.5,
                    clip: true,
                },
                transform: [{ regression: escapedGene, on: escapedGene2 }],
            },
            {
                mark: { type: "circle", tooltip: { content: "data" } },
                encoding: {
                    color: {
                        field: "metacell_type",
                        scale: { range: { field: "metacell_color" } },
                        legend: null,
                    },
                },
                params: [
                    // Pan and zoom plot
                    { name: "brush", select: "interval", bind: "scales" },
                ],
            },
        ],
    };
    vegaEmbed(id, chart).catch(console.error);
}
