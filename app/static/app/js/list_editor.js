// Functions to get, set and append user lists
function parseID(str) {
    if (str.includes("gene_list")) {
        return "gene_list";
    }
    return "list";
}

function getLocalStorageLists(id) {
    id = parseID(id);
    return JSON.parse( localStorage.getItem(id) ) || {};
}

function setLocalStorageLists(id, lists) {
    id = parseID(id);
    localStorage.setItem(id, JSON.stringify(lists));
}

function getUserLists(id, species, name = undefined) {
    var lists = getLocalStorageLists(id);
    if (name === undefined) {
        return lists[species] || [];
    } else {
        return lists[species].find(item => item.name == name) || [];
    }
}

function setUserList(id, species, name, values, group='Custom lists', color='gray') {
    var lists = getLocalStorageLists(id);

    // Create species key if not present
    lists[species] ||= [];

    lists[species].push({
        name: name,
        items: values,
        color: color,
        group: group
    });

    // Sort by group
    lists[species].sort((a, b) => a.group.localeCompare(b.group));

    setLocalStorageLists(id, lists);
}

function findUserListIndex(list, name) {
    return list.findIndex(item => item.name === name);
}

function renameUserList(id, species, name, newName) {
    var lists = getLocalStorageLists(id);
    var index = findUserListIndex(lists[species], name);
    lists[species][index].name = newName;
    setLocalStorageLists(id, lists);
}

function resetUserLists(id, species) {
    var lists = getLocalStorageLists(id);
    delete lists[species];
    setLocalStorageLists(id, lists);
}

function removeUserList(id, species, name) {
    var lists = getLocalStorageLists(id);
    if (species in lists) {
        var index = findUserListIndex(lists[species], name);
        lists[species].splice(index, 1);
        setLocalStorageLists(id, lists);
    } else {
        console.error(`Cannot delete list ${name}: list is not available for ${species}`);
    }
}

function getAllLists(id) {
    let res = $(`#${id}_options a`).map(function() {
        return {
            name: $(this).data('list'),
            count: $(this).data('count'),
            color: $(this).data('color'),
            group: $(this).data('group')
        };
    }).get();
    return res;
}

function getAllListNames(id) {
    // Get names of all rendered lists
    var lists = $(`#${id}_options a`)
        .map((index, item) => $(item).data('list'))
        .get();
    return lists;
}

function appendUserList(id, species, name, values, group='Custom lists', color='gray') {
    var lists = getUserLists(id, species);
    var allListNames = getAllListNames(id);

    // Ensure new list name is unique
    while (allListNames.includes(name)) {
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

    // Assign new values to list
    setUserList(id, species, name, values, group, color);
    redrawUserLists(id, species, active=name);
}

// Render user group headings and items
function appendListGroupHeading (id, group) {
    const template = document.getElementById(`${id}_heading`);
    const container = document.getElementById(`${id}_options`);

    const isPreset = group === 'preset';

    // Render each list based on template
    var $clone = $(document.importNode(template.content, true));
    $clone.find(`div`)
        .text(isPreset ? 'Preset gene lists' : group)
        .attr("data-group", group);

    if (isPreset) {
        const readonly = '<span class="text-muted"><i class="fa fa-lock fa-2xs"></i> read-only</span>';
        $clone.find(`div`).html('Preset gene lists' + readonly);
    }

    container.appendChild($clone[0]);
}

function appendListGroupItem (id, name, group, count, active=false) {
    const template = document.getElementById(`${id}_element`);
    const container = document.getElementById(`${id}_options`);

    // Render each list based on template
    var $clone = $(document.importNode(template.content, true));

    $clone.find(`.${id}_group_a`)
        .attr("data-list", name)
        .attr("data-group", group || 'preset')
        .attr("data-count", count || 0)
        .attr("data-color", 'orange');

    $clone.find(`.${id}_group_title`).text(name);
    $clone.find(`.${id}_group_count`).text(count);

    container.appendChild($clone[0]);

    if (active) {
        $(container).find('a').removeClass('active');
        $(container).children('a:last').addClass('active').click();
    }
}

function drawUserLists (id, species, activeList=[]) {
    // Render all user lists (sorted by group)
    var lists = getUserLists(id, species);

    group = '';
    for (const index in lists) {
        const elem = lists[index];
        var active = activeList.includes(elem.name);
        if (elem.group != group) {
            appendListGroupHeading(id, elem.group);
            group = elem.group;
        }
        const len = elem.items ? elem.items.length : 0;
        appendListGroupItem(id, elem.name, elem.group, len, active=active);
    };
}


function clearSearch(id) {
    var search = $(`#${id}_search`);
    search.val('');

    // Trigger input event as if the user cleared the search box
    search[0].dispatchEvent(new Event('input'));
}

function redrawUserLists (id, species, activeList=[]) {
    clearSearch(id);

    // Delete all user lists from interface
    const container = document.getElementById(`${id}_options`);
    $(container).find('*[data-group]:not([data-group="preset"]').remove();

    drawUserLists(id, species, activeList);
}

/* Prepare URLs to retrieve gene information for a given list */
function getGenesFromListURL (url, species, genelist, limit = undefined) {
    var params = new URLSearchParams({
	    species: species,
	    genes: genelist
	});

	if (limit !== undefined) {
	    params.append('limit', limit)
	}
	return url + "?" + params.toString();
}

function getGenesURL (url, species, genes) {
    var params = new URLSearchParams({
	    species: species,
	    genes: genes.join(',')
	});
	return url + "?" + params.toString();
}

async function fetchAllGenesFromList (id, species, apiURL, name, group) {
    var genes;
    if (group === 'preset') {
        var url = getGenesFromListURL(apiURL, species, name, limit=0);
        const response = await fetch(url);
        const data = await response.json();
        genes = data.map(item => item.name);
    } else {
        genes = getUserLists(id, species, name).items;
    }
    return genes;
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

    // Load data depending on list group
    var name = $(`#${id}_options`).find(".active").data('list');
    var group = $(`#${id}_options`).find(".active").data('group');

    var url;
    if (group === 'preset') {
        url = getGenesFromListURL(url, species, name);
    } else {
        var genes = getUserLists(id, species, name).items;
        url = genes.length === 0 ? '' : getGenesURL(url, species, genes);
    }
    table.ajax.url(url || '').load();

    // Update list-specific controls
    $(`#${id}_controls`).prop('disabled', group === 'preset');
}

function createUserListsFromFile (elem, id, species, maxMB = 10) {
    const file = elem.files[0];

    if (!file) {
        console.error('Error uploading file: no file selected');
        return;
    }

    if (file.size > maxMB * 1024 * 1024) {
        alert(`Size limit of ${maxMB} MB exceeded.`);
    } else {
        const reader = new FileReader();
        reader.onload = function (e) {
            const content = e.target.result;
            const lines = content.split("\n");

            // Detect delimiter
            const delimiter = content.indexOf(",") > content.indexOf("\t") ? "," : "\t";

            const dict = {};
            lines.forEach(function (line) {
                const columns = line.split(delimiter);
                if (columns.length > 1) {
                    let [key, value] = columns.map(str => str.trim());
                    dict[key] ||= [];
                    dict[key].push(value);
                }
            });

            // Append user lists
            for (const key in dict) {
                appendUserList(id, species, key, dict[key], 'Uploaded lists');
            }
        };
        reader.readAsText(file);
    }
    // Clear selection to allow uploading the same file again
    $(elem).val("");
}
