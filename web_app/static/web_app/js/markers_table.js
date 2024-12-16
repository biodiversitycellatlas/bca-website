// Link to gene
function linkGene (data, type, row) {
    if (type === 'display') {
        data = `<a href=${gene_url}?gene=${data}>${data}</a>`;
    }
    return data;
}

// Round numeric values
function round (data, type, row) {
    if (type === 'display' || type === 'filter') {
        return parseFloat(data).toFixed(2);
    }
    return data;
}

// Improve array parsing
function parseArray (data, type, row) {
    if (Array.isArray(data)) {
        return data.join(', ');
    }
    return data;
}

// Create DataTable
function createMarkersTable(id, url, species, metacells, fc_min_type, fc_min, fc_max_bg_type, fc_max_bg) {
	var params = new URLSearchParams({
	    species: species,
		metacells: metacells,
		fc_min_type: fc_min_type,
		fc_min: fc_min,
		fc_max_bg_type: fc_max_bg_type,
		fc_max_bg: fc_max_bg,
		limit: 0
	});
	var apiURL = url + "?" + params.toString();

    $(id).dataTable({
        ajax: { url: apiURL, dataSrc: function (json) { return json; } },
        pageLength: 25,
        scrollX: true,
        columns: [
            { data: 'name', title: "Gene ID", render: linkGene },
            { data: 'description', title: "Description", className: 'truncate' },
            { data: 'domains', title: "Domains", render: parseArray, className: 'truncate' },
            { data: 'fg_sum_umi', title: "Total UMIs", render: round },
            { data: 'umi_perc', title: "UMI %", render: round },
            { data: 'fg_mean_fc', title: "Mean FC", render: round },
            { data: 'fg_median_fc', title: "Median FC", render: round }
        ],
        createdCell: function(td, cellData, rowData, row, col) {
            if ($(td).hasClass('truncate')) {
                $(td).attr('title', cellData);
            }
        }
    });
}
