// Link to gene
function linkGene (data, type, row) {
    if (type === 'display') {
        data = `<a href=${gene_url}${data}>${data}</a>`;
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
function createListEditorTable(id, url) {
    console.log(url);
    $(`#${id}`).dataTable({
        ajax: {
            url: url,
            data: function(data) {
                var params = {
                    offset: data.start,
                    limit: data.length,
                    q: data.search.value
                };
                return params;
            },
            dataFilter: function (data) {
                var json = jQuery.parseJSON( data );
                json.recordsTotal = json.count;
                json.recordsFiltered = json.count;
                json.data = json.list;
                return JSON.stringify( json );
            },
            dataSrc: function (json) { return json.results; },
        },
        pageLength: 25,
        processing: true,
        serverSide: true,
        select: true,
        rowId: 'name',
        scrollX: true,
        language: {
            info: "Total entries: _TOTAL_"
        },
        columns: [
            { data: 'name', title: "Gene", render: linkGene },
            { data: 'description', title: "Description", className: 'truncate' },
            { data: 'domains', title: "Domains", render: parseArray, className: 'truncate' }
        ],
        order: [[5, 'des']],
        createdCell: function(td, cellData, rowData, row, col) {
            if ($(td).hasClass('truncate')) {
                $(td).attr('title', cellData);
            }
        }
    });
}
