// Link to gene
function linkGene(data, type, row) {
    if (type === "display") {
        data = `<a href=${gene_url}${data}>${data}</a>`;
    }
    return data;
}

// Round numeric values
function round(data, type, row) {
    if (type === "display" || type === "filter") {
        return parseFloat(data).toFixed(2);
    }
    return data;
}

// Improve array parsing
function parseArray(data, type, row) {
    if (Array.isArray(data)) {
        return data.join(", ");
    }
    return data;
}

// Create DataTable
function createMarkersTable(id, url) {
    $(`#${id}_table`).dataTable({
        ajax: {
            url: url,
            dataSrc: function (json) {
                return json;
            },
        },
        pageLength: 25,
        scrollX: true,
        columns: [
            { data: "name", title: "Gene ID", render: linkGene },
            {
                data: "description",
                title: "Description",
                className: "truncate",
            },
            {
                data: "domains",
                title: "Domains",
                render: parseArray,
                className: "truncate",
            },
            { data: "genelists", title: "Gene lists", className: "truncate" },
            { data: "fg_sum_umi", title: "Total UMIs" },
            { data: "umi_perc", title: "UMI %", render: round },
            { data: "fg_mean_fc", title: "Mean FC", render: round },
            { data: "fg_median_fc", title: "Median FC", render: round },
        ],
        order: [[5, "des"]],
        createdCell: function (td, cellData, rowData, row, col) {
            if ($(td).hasClass("truncate")) {
                $(td).attr("title", cellData);
            }
        },
    });
}
