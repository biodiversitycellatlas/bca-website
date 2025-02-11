// Functions to get, set and append custom lists
function getCustomLists(id, species, name) {
    var lists = JSON.parse( localStorage.getItem(id) ) || {};

    if (species === undefined) {
        return lists;
    } else if (name === undefined) {
        return lists[species];
    } else {
        return lists[species][name];
    }
}

function resetCustomLists(id, species) {
    var lists = getCustomLists(id);
    delete lists[species];
    localStorage.setItem(id, JSON.stringify(lists));
}

function setCustomList(id, species, name, values) {
    var lists = getCustomLists(id);
    if (Object.keys(lists).length === 0) {
        lists[species] = {};
    }
    lists[species][name] = values;
    localStorage.setItem(id, JSON.stringify(lists));
}

function removeCustomList(id, species, name) {
    var lists = getCustomLists(id);
    if (lists[species] !== undefined) {
        delete lists[species][name];
    }
    localStorage.setItem(id, JSON.stringify(lists));
}

function appendCustomList(id, species, name, values) {
    var lists = getCustomLists(id, species);

    if (lists === undefined) {
        // Create new object if not available
        lists = {};
    } else {
        // Ensure new list name is unique
        while (lists[name]) {
            const match = name.match(/(.*?) (\d+)$/);
            if (match) {
                // Increase index in the name
                index = parseInt(match[2]) + 1;
                name = match[1];
            } else {
                // Append 2 if there is no index
                index = 2;
            }
            name += ' ' + index;
        }
    }

    // Assign new values to list
    setCustomList(id, species, name, values);
    appendListGroupItem(id, name, 'custom', values.length, index=0);
}

function renameCustomList(id, species, name, newName) {
    var values = getCustomLists(id, species, name);
    removeCustomList(id, species, name);
    setCustomList(id, species, newName, values);
}

// Render custom groups
function appendListGroupItem (id, name, type, gene_count, index=0, firstRender=false) {
    const template = document.getElementById(`${id}_element`);
    const container = document.getElementById(`${id}_options`);

    // Render each list based on template
    var $clone = $(document.importNode(template.content, true));

    $clone.find(`.${id}_group_a`)
        .attr("data-list", name)
        .attr("data-type", type || 'preset');

    // Set first element to active if first data table rendering
    if (firstRender && index === 0) {
        $clone.find(`.${id}_group_a`).addClass('active');
    }

    $clone.find(`.${id}_group_title`).text(name);
    $clone.find(`.${id}_group_count`).text(`${gene_count} genes`);

    if (type === 'custom') {
        userLabel = `Custom <i class="fa fa-user fa-xs fa-fw"></i>`;
        $clone.find(`.${id}_group_type`).html(userLabel);
    }
    container.appendChild($clone[0]);

    if (!firstRender && index === 0) {
        $(container).find('a').removeClass('active');
        $(container).children('a:last').addClass('active').click();
    }
}

function redrawCustomLists (id, species) {
    // Delete all custom lists from interface
    const container = document.getElementById(`${id}_options`);
    $(container).find('a[data-type="custom"]').remove();

    // Re-render all custom lists
    var customLists = getCustomLists(id, species);
    for (var name in customLists) {
        var count = customLists[name].length
        appendListGroupItem(id, name, 'custom', count);
    }
}

function getGenesFromListURL (url, species, genelist) {
    var params = new URLSearchParams({
	    species: species,
	    genelists: genelist
	});
	return url + "?" + params.toString();
}

function getGenesURL (url, species, genes) {
    var params = new URLSearchParams({
	    species: species,
	    genes: genes.join(',')
	});
	return url + "?" + params.toString();
}

/**
 * Renders details for a selected list.
 *
 * @param {string} id - Identifier.
 * @param {string} species - Species.
 * @param {string} url - URL to retrieve genes.
 */
function renderListDetail (id, species, url) {
    var table = $(`#${id}_editor_table`).DataTable();
    table.search('').columns().search(''); // Clear search
    table.clear(); // Clear data

    // Load data depending on list type
    var name = $(`#${id}_options`).find(".active").attr('data-list');
    var type = $(`#${id}_options`).find(".active").attr('data-type');

    var url;
    if (type === 'preset') {
        url = getGenesFromListURL(url, species, name);
    } else if (type === 'custom')  {
        var genes = getCustomLists(id, species, name);
        url = genes.length === 0 ? '' : getGenesURL(url, species, genes);
    }
    table.ajax.url(url || '').load();

    // Update list-specific controls
    $(`#${id}_rename`).val(name);
    $(`#${id}_controls`).prop('disabled', type === 'preset');
}