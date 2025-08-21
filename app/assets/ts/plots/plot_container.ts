/**
 * Loading spinners in plot containers.
 *
 * Expects container elements to follow the convention:
 *   - Plot container:   <id>-plot
 *   - Spinner element:  <id>-spinner
 */

import $ from "jquery";

/**
 * Get the spinner element for a given container id.
 * @param {string} id - Base id of the container.
 * @returns {HTMLElement|null} Spinner element, or null if not found.
 */
function getSpinner(id) {
    return document.getElementById(id + "-spinner");
}

/**
 * Hide the spinner inside a container.
 * @param {string} id - Base id of the container.
 */
export function hideSpinner(id) {
    var spinner = getSpinner(id);
    if (spinner !== null) {
        spinner.style.display = "none";
    }
}

/**
 * Show the spinner inside a container.
 * @param {string} id - Base id of the container.
 */
export function showSpinner(id) {
    var spinner = getSpinner(id);
    if (spinner !== null) {
        spinner.style.display = "flex";
    }
}

/**
 * Clear a plot container by inserting a loading spinner.
 * @param {string} id - Base id of the container.
 */
export function clearContainer(id) {
    $("#" + id + "-plot").html(
        `<div id="${id}-spinner" class="loading-state">
            <div class="loader"></div>
        </div>`,
    );
}
