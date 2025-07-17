function createExpressionBubblePlot(id, gene, data) {
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
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
    vegaEmbed(id, chart)
        .then((res) => {
            viewExpression = res.view;
        })
        .catch(console.error);
}

function plotGeneExpressionComparison(id, dataset, gene, gene2, url, stats) {
    // Create URL to fetch expression data for both genes
    var params = new URLSearchParams({
        genes: `${gene},${gene2}`,
        dataset: dataset,
        limit: 0,
    });
    var apiURL = url + "?" + params.toString().replace(/%2C/g, ",");
    updateDataMenu(id, apiURL, "Expression comparison (plot data)");

    // Fetch data from the API and create plot
    clearContainer(id);
    showSpinner(id);
    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            createExpressionComparisonPlot(
                `#${id}-plot`,
                gene,
                gene2,
                data,
                stats,
            );
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        })
        .finally(() => {
            hideSpinner(id);
        });
}

function createExpressionComparisonPlot(id, gene, gene2, data, stats) {
    var chart = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
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
                    { op: "min", field: gene, as: "xMin" },
                    { op: "max", field: gene, as: "xMax" },
                    { op: "min", field: gene2, as: "yMin" },
                    { op: "max", field: gene2, as: "yMax" },
                ],
            },
            { calculate: "min(datum.xMin, datum.yMin)", as: "min" },
            { calculate: "max(datum.xMax, datum.yMax)", as: "max" },
        ],
        data: { name: "data", values: data },
        width: "container",
        encoding: {
            x: {
                field: gene,
                type: "quantitative",
                title: gene + " fold-change",
                scale: {
                    domain: {
                        expr: "[data('data_0')[0]['min'], data('data_0')[0]['max']]",
                    },
                },
            },
            y: {
                field: gene2,
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
                transform: [{ regression: gene, on: gene2 }],
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
    vegaEmbed(id, chart)
        .then((res) => {
            viewExpression = res.view;
        })
        .catch(console.error);
}
