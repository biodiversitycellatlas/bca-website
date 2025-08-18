/* global $ */

// Loading spinner functions
function getSpinner(id) {
    return document.getElementById(id + "-spinner");
}

export function hideSpinner(id) {
    var spinner = getSpinner(id);
    if (spinner !== null) {
        spinner.style.display = "none";
    }
}

export function showSpinner(id) {
    var spinner = getSpinner(id);
    if (spinner !== null) {
        spinner.style.display = "flex";
    }
}

// Reset container with a plot to show spinner
export function clearContainer(id) {
    $("#" + id + "-plot").html(
        `<div id="${id}-spinner" class="loading-state"><div class="loader"></div></div>`,
    );
}
