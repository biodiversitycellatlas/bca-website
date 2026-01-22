/**
 * Clipboard functions.
 */

import $ from "jquery";

/**
 * Copy the current page URL to the clipboard and temporarily show confirmation
 * tooltip.
 *
 * @param {string} id - Hash fragment to append to the URL (optional).
 * @param {HTMLElement} elem - Button element triggering the copy action.
 */
function handleCopyURL(elem, id = "") {
    var clipboard = $(elem);
    clipboard.prop("disabled", true);

    let url = new URL(window.location.href);
    if (id !== "") {
        url.hash = `#${id}`;
    }
    navigator.clipboard.writeText(url.href);
    clipboard.tooltip("show");

    setTimeout(function () {
        clipboard.tooltip("hide");
        clipboard.prop("disabled", false);
    }, 1500);
}

/**
 * Initialize a clipboard button to copy the current page URL when clicked.
 *
 * @param {string} id - Identifier for the button and optional hash fragment.
 */
export function initClipboardButton(id) {
    $(`#clipboard_${id}`).on("click", function () {
        handleCopyURL(this, id);
    });
}
