import { getDataPortalUrl } from "../../utils/urls.js";

function makeLinkGene(dataset) {
    return function linkGene(data, type, row) {
        if (type === "display") {
            let url = getDataPortalUrl("atlas_gene", dataset, data);
            if (url) {
                data = `<a href=${url}>${data}</a>`;
            }
        }
        return data;
    }
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
export function createMarkersTable(id, dataset, url) {
    let linkGene = makeLinkGene(dataset);
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
