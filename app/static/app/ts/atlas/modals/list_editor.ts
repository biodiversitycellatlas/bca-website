/**
 * Dataset selectize element.
 */

import $ from "jquery";
import "datatables.net-bs5";
import "datatables.net-select-bs5";

import { getDataPortalUrl } from "../../utils/urls.ts";
import { highlightMatch } from "../../utils/utils.ts";
import { createGeneTable } from "../tables/gene_table.ts";
import { getSelectedRows } from "../tables/utils.ts";

/**
 * Normalizes list identifier.
 */
function parseID(str) {
    if (str.includes("gene_list")) {
        return "gene_list";
    }
    return "list";
}

/**
 * Retrieves stored lists from localStorage.
 */
function getLocalStorageLists(id) {
    id = parseID(id);
    return JSON.parse(localStorage.getItem(id)) || {};
}

/**
 * Saves lists to localStorage.
 */
function setLocalStorageLists(id, lists) {
    id = parseID(id);
    localStorage.setItem(id, JSON.stringify(lists));
}

/**
 * Retrieve user lists for a given species from localStorage.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {string} [name] - Optional list name to retrieve.
 * @returns {Array|Object} Matching list(s).
 */
export function getUserLists(id, species, name = undefined) {
    var lists = getLocalStorageLists(id);
    if (name === undefined) {
        return lists[species] || [];
    } else {
        return lists[species].find((item) => item.name == name) || [];
    }
}

/**
 * Store a new user list under the given species.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {string} name - List name.
 * @param {Array} values - Array of items to store.
 * @param {string} [group='Custom lists'] - Group name.
 * @param {string} [color='gray'] - Display color.
 */
function setUserList(
    id,
    species,
    name,
    values,
    group = "Custom lists",
    color = "gray",
) {
    var lists = getLocalStorageLists(id);

    // Create species key if not present
    lists[species] ||= [];

    lists[species].push({
        name: name,
        items: values,
        color: color,
        group: group,
    });

    // Sort by group
    lists[species].sort((a, b) => a.group.localeCompare(b.group));

    setLocalStorageLists(id, lists);
}

/**
 * Find the index of a user list by name.
 */
function findUserListIndex(list, name) {
    return list.findIndex((item) => item.name === name);
}

/**
 * Rename user list.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {string} name - Current list name.
 * @param {string} newName - New list name.
 */
function renameUserList(id, species, name, newName) {
    let lists = getLocalStorageLists(id);
    let index = findUserListIndex(lists[species], name);
    lists[species][index].name = newName;
    setLocalStorageLists(id, lists);
}

/**
 * Remove all user lists for a species from localStorage.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 */
function resetUserLists(id, species) {
    var lists = getLocalStorageLists(id);
    delete lists[species];
    setLocalStorageLists(id, lists);
}

/**
 * Delete a specific user list for a species.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {string} name - Name of the list to remove.
 */
function removeUserList(id, species, name) {
    let lists = getLocalStorageLists(id);
    if (species in lists) {
        let index = findUserListIndex(lists[species], name);
        lists[species].splice(index, 1);
        setLocalStorageLists(id, lists);
    } else {
        console.error(
            `Cannot delete list ${name}: list is not available for ${species}`,
        );
    }
}

/**
 * Collect all (database and user-created lists) lists from the DOM.
 *
 * @param {string} id - Base identifier.
 * @returns {Array<Object>} List metadata (name, count, color, group).
 */
export function getAllLists(id) {
    let res = $(`#${id}_options a`)
        .map(function () {
            return {
                name: $(this).data("list"),
                count: $(this).data("count"),
                color: $(this).data("color"),
                group: $(this).data("group"),
            };
        })
        .get();
    return res;
}

/**
 * Get names of all rendered lists from the DOM.
 *
 * @param {string} id - Base identifier.
 * @returns {Array<string>} Names of lists.
 */
function getAllListNames(id) {
    // Get names of all rendered lists
    var lists = $(`#${id}_options a`)
        .map((index, item) => $(item).data("list"))
        .get();
    return lists;
}

/**
 * Appends a new user list with unique naming and updates the UI.
 *
 * @param {string} id - User identifier.
 * @param {string} species - Species identifier.
 * @param {string} name - Name for the new list. If already existing, the name
 * will have a number appended or incremented.
 * @param {Array} values - Array of values to store in the list.
 * @param {string} [group='Custom lists'] - Group name for categorization.
 * @param {string} [color='gray'] - Color assigned to the list.
 * @param {boolean} [redraw=true] - Whether to update the UI after adding the list.
 * If adding multiple lists, manually call redrawUserLists to only set the last
 * list as active (see example).
 *
 * @returns {string} - Unique name assigned to the list. If the name given
 * already exists, a number is appended or incremented.
 *
 * @example
 * // When appending multiple lists, set redraw=false and manually update the UI:
 * var name;
 * for (name in lists) {
 *     name = appendUserList(id, species, name, lists[name], group="Group",
 *                           color='gray', redraw=false);
 * }
 * redrawUserLists(id, species, active=[name]);
 */
export function appendUserList(
    id,
    species,
    name,
    values,
    group = "Custom lists",
    color = "gray",
    redraw = true,
) {
    let allListNames = getAllListNames(id);
    let index;

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
        name += " " + index;
    }

    // Assign new values to list
    setUserList(id, species, name, values, group, color);

    // Redraw user lists
    if (redraw) redrawUserLists(id, species, [name]);
    return name;
}

/**
 * Return the currently active list DOM element.
 *
 * @param {string} id - Base identifier.
 * @returns {jQuery} Active list element.
 */
function getSelectedList(id) {
    return $(`#${id}_options button.active`);
}

/**
 * Render a group heading in the list panel.
 *
 * @param {string} id - Base identifier.
 * @param {string} group - Group name.
 */
function appendListGroupHeading(id, group) {
    const template = document.getElementById(`${id}_heading`);
    const container = document.getElementById(`${id}_options`);

    const isPreset = group === "preset";

    // Render each list based on template
    var $clone = $(document.importNode(template.content, true));
    $clone.find(`div`).text(group).attr("data-group", group);

    if (isPreset) {
        const readonly =
            '<span class="text-muted"><i class="fa fa-lock fa-2xs"></i><span class="d-none d-lg-inline"> read-only</span></span>';
        $clone.find(`div`).html("Preset lists" + readonly);
    }

    container.appendChild($clone[0]);
}

/**
 * Render a list item under the given group.
 *
 * @param {string} id - Base identifier.
 * @param {string} name - List name.
 * @param {string} group - Group name.
 * @param {number} count - Number of items in the list.
 * @param {boolean} [active=false] - Whether the item is active.
 */
function appendListGroupItem(id, name, group, count, active = false) {
    const template = document.getElementById(`${id}_element`);
    const container = document.getElementById(`${id}_options`);

    // Render each list based on template
    var $clone = $(document.importNode(template.content, true));

    $clone
        .find(`.${id}_group_a`)
        .attr("data-list", name)
        .attr("data-group", group || "preset")
        .attr("data-count", count || 0)
        .attr("data-color", "orange");

    $clone.find(`.${id}_group_title`).text(name);
    $clone.find(`.${id}_group_count`).text(count);

    container.appendChild($clone[0]);

    if (active) {
        $(container).find("a").removeClass("active");
        $(container).children("a:last").addClass("active").click();
    }
}

/**
 * Render all user lists grouped by category.
 *
 * @param {string} id - Base identifier for UI elements.
 * @param {string} species - Species identifier.
 * @param {Array<string>} [activeList=[]] - Lists to mark active.
 */
function drawUserLists(id, species, activeList = []) {
    // Render all user lists (sorted by group)
    let lists = getUserLists(id, species);

    let group = "";
    for (const index in lists) {
        const elem = lists[index];
        let active = activeList.includes(elem.name);
        if (elem.group != group) {
            appendListGroupHeading(id, elem.group);
            group = elem.group;
        }
        const len = elem.items ? elem.items.length : 0;
        appendListGroupItem(id, elem.name, elem.group, len, active);
    }
}

/**
 * Clear the search box.
 *
 * @param {string} id - Base identifier.
 */
function clearSearch(id) {
    let search = $(`#${id}_search`);
    search.val("");

    // Trigger input event as if the user cleared the search box
    if (search.length) search[0].dispatchEvent(new Event("input"));
}

/**
 * Refresh the displayed user lists in the UI.
 * Clears search, removes current lists, and redraws.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {Array<string>} [activeList=[]] - Lists to mark active.
 */
export function redrawUserLists(id, species, activeList = []) {
    clearSearch(id);

    // Delete all user lists from interface
    const container = document.getElementById(`${id}_options`);
    $(container).find('*[data-group]:not([data-group="preset"]').remove();

    drawUserLists(id, species, activeList);
}

/**
 * Construct a URL for fetching genes in a given list.
 *
 * @param {string} url - Base API endpoint.
 * @param {string} species - Species identifier.
 * @param {string} genelist - Name of the gene list.
 * @param {number} [limit] - Optional limit on results.
 * @returns {string} Full request URL.
 */
function getGenesFromListURL(url, species, genelist, limit = undefined) {
    var params = new URLSearchParams({
        species: species,
        genes: genelist,
    });

    if (limit !== undefined) {
        params.append("limit", limit);
    }
    return url + "?" + params.toString();
}

/**
 * Construct a URL for fetching a set of genes.
 *
 * @param {string} url - Base API endpoint.
 * @param {string} species - Species identifier.
 * @param {Array<string>} genes - Gene names.
 * @returns {string} Full request URL.
 */
function getGenesURL(url, species, genes) {
    var params = new URLSearchParams({
        species: species,
        genes: genes.join(","),
    });
    return url + "?" + params.toString();
}

/**
 * Fetch information on all genes from a specific list.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {string} apiURL - API endpoint.
 * @param {string} name - List name.
 * @param {string} group - List group.
 * @returns {Promise<Array<string>>} Gene names.
 */
async function fetchAllGenesFromList(id, species, apiURL, name, group) {
    var genes;
    if (group === "preset") {
        var url = getGenesFromListURL(apiURL, species, name, 0);
        const response = await fetch(url);
        const data = await response.json();
        genes = data.map((item) => item.name);
    } else {
        genes = getUserLists(id, species, name).items;
    }
    return genes;
}

/**
 * Render list details when the active list changes.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 */
export function renderActiveList(id, species) {
    // Get data and render table for active group list
    let previousActiveList = null;

    // Trigger data rendering on any change to .active class
    $(`#${id}_options`).on("click keyup", ".active", function (event) {
        // Prevent event triggering if element was previously active
        if (previousActiveList && previousActiveList.is($(this))) {
            event.preventDefault();
            return;
        }
        previousActiveList = $(this);
        renderListDetail(id, species);
    });
}

/**
 * Renders details for a selected list.
 *
 * @param {string} id - Identifier.
 * @param {string} species - Species.
 */
function renderListDetail(id, species) {
    var table = $(`#${id}_editor_table`).DataTable();
    table.search("").columns().search(""); // Clear search
    table.clear(); // Clear data

    // Load data depending on list group
    var name = $(`#${id}_options`).find(".active").data("list");
    var group = $(`#${id}_options`).find(".active").data("group");

    let url = getDataPortalUrl("rest:gene-list");
    if (group === "preset") {
        url = getGenesFromListURL(url, species, name);
    } else {
        var genes = getUserLists(id, species, name).items;
        url = genes.length === 0 ? "" : getGenesURL(url, species, genes);
    }
    table.ajax.url(url || "").load();

    // Update list-specific controls
    $(`#${id}_controls`).prop("disabled", group === "preset");
}

/**
 * Create user lists from uploaded file.
 *
 * @param {HTMLElement} elem - File input element.
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {number} [maxMB=10] - Maximum file size allowed in MB.
 */
function createUserListsFromFile(elem, id, species, maxMB = 10) {
    const file = elem.files[0];

    if (!file) {
        console.error("Error uploading file: no file selected");
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
            const delimiter =
                content.indexOf(",") > content.indexOf("\t") ? "," : "\t";

            const dict = {};
            lines.forEach(function (line) {
                const columns = line.split(delimiter);
                if (columns.length > 1) {
                    let [key, value] = columns.map((str) => str.trim());
                    dict[key] ||= [];
                    dict[key].push(value);
                }
            });

            // Append user lists
            var name;
            for (const key in dict) {
                name = appendUserList(
                    id,
                    species,
                    key,
                    dict[key],
                    "Uploaded lists",
                    false,
                );
            }
            redrawUserLists(id, species, [name]);
        };
        reader.readAsText(file);
    }
    // Clear selection to allow uploading the same file again
    $(elem).val("");
}

/**
 * Load and render preset gene lists.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {Object} dataset - Dataset reference for table creation.
 */
export function loadGeneLists(id, species, dataset) {
    let url = getDataPortalUrl("rest:genelist-list", null, null, null, {
        species: species,
    });
    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            appendListGroupHeading(id, "preset");
            data.results.forEach((item) => {
                appendListGroupItem(id, item.name, item.type, item.gene_count);
            });
            drawUserLists(id, species);
        })
        .then(() => {
            // Create gene table
            createGeneTable(`${id}_editor_table`, dataset);
            // Update interface based on selection
            var table = $(`#${id}_editor_table`).DataTable();
            table.on("select deselect", function (e, dt, type) {
                if (type === "row") {
                    const len = getSelectedRows(`${id}_editor_table`).length;
                    var label = `${len} selected gene` + (len === 1 ? "" : "s");
                    $(`#${id}_new_selected_count`).text(label);

                    // Disable element if no rows are selected
                    if (len === 0) {
                        $(`#${id}_new_selected`).addClass("disabled");
                    } else {
                        $(`#${id}_new_selected`).removeClass("disabled");
                    }
                }
            });
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        });
}

/**
 * Attach UI actions for managing gene lists.
 *
 * @param {string} id - Base identifier.
 * @param {string} species - Species identifier.
 * @param {number} maxFileSize - Maximum upload size in MB.
 */
export function loadMenuActions(id, species, maxFileSize) {
    // Menu action: New list
    $(`#${id}_new_empty`).on("click", function () {
        appendUserList(id, species, "Empty list", []);
    });

    $(`#${id}_new_selected`).on("click", function () {
        const selected = getSelectedRows(`${id}_editor_table`);
        appendUserList(id, species, "Selected genes", selected);
    });

    // Menu action: Reset
    $(`#${id}_reset`).on("click", function () {
        if (
            confirm(`Do you want to reset all user gene lists for ${species}?`)
        ) {
            resetUserLists(id, species);
            redrawUserLists(id, species);

            // Select the first item in the list if no element is selected
            if ($(`#${id}_options`).find("a.active").length === 0) {
                $(`#${id}_options a`).first().addClass("active").click();
            }
        }
    });

    // Menu action: Rename
    $(`#${id}_rename_btn`).on("click", function () {
        var activeItem = $(`#${id}_options`).find("a.active");
        var oldName = activeItem.find(`.${id}_group_title`).text();

        var newName = prompt("Rename list:", oldName);
        if (newName === "") {
            // Avoid empty list name
            alert("The name of a list cannot be empty.");
            return;
        } else if (newName === null) {
            // Cancel rename
            return;
        }

        // Avoid duplicated name
        var all_names = $(`#${id}_options`)
            .find(`a .${id}_group_title`)
            .map((i, el) => $(el).text())
            .get();

        if (all_names.includes(newName)) {
            alert("This list name is already in use.");
            return;
        }

        renameUserList(id, species, oldName, newName);
        redrawUserLists(id, species, [newName]);
    });

    // Menu action: Remove
    $(`#${id}_remove`).on("click", function () {
        var activeItem = $(`#${id}_options`).find("a.active");
        var name = activeItem.find(`.${id}_group_title`).text();

        if (confirm(`Do you want to remove the following list: ${name}?`)) {
            removeUserList(id, species, name);
            redrawUserLists(id, species);

            // Select the first item in the list if no element is selected
            if ($(`#${id}_options`).find("a.active").length === 0) {
                $(`#${id}_options a`).first().addClass("active").click();
            }
        }
    });

    // Menu action: duplicate
    $(`#${id}_new_duplicate`).on("click", function () {
        let activeItem = getSelectedList(id);
        let name = activeItem.data("list");
        let group = activeItem.data("group");

        let url = getDataPortalUrl("rest:gene-list");
        fetchAllGenesFromList(id, species, url, name, group)
            .then((genes) => {
                appendUserList(id, species, name, genes);
            })
            .catch((error) => {
                console.error("Error fetching genes:", error);
            });
    });

    // Menu action: upload file containing lists
    $(`#${id}_new_upload`).on("change", function () {
        createUserListsFromFile(this, id, species, maxFileSize);
    });

    // Filter by list name
    $(`#${id}_search`).on("input search", function () {
        const query = this.value.toLowerCase(); // lowercase comparison

        // Hide lists that do not match query value
        var elems = $(`#${id}_options a`);
        elems.each(function () {
            const title = $(this).find(`.${id}_group_title`);
            if (title.text().toLowerCase().includes(query)) {
                $(this).removeClass("d-none");
            } else {
                $(this).addClass("d-none");
            }
            title.html(highlightMatch(title.text(), query));
        });
    });
}
