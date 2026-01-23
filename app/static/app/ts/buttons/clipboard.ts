/**
 * Clipboard functions.
 */

import $ from "jquery";

/**
 * Copies text to the clipboard and shows temporary visual feedback.
 *
 * @param {HTMLElement|jQuery} elem - Element triggering the copy action
 * @param {string} data - Text to copy to the clipboard
 * @param {number} timeout - Duration (ms) before restoring original state
 */
export function copyToClipboard(elem, data, timeout = 1000) {
    const $elem = $(elem);
    const originalHTML = $elem.html();
    const textSpan = $elem.find("span.label");
    $elem.addClass("disabled");

    navigator.clipboard.writeText(data);

    // Replace text with confirmation with fade animation
    textSpan.fadeOut(150, function () {
        textSpan
            .html("<i class='fa fa-check fa-bounce'></i> Copied")
            .fadeIn(150);
    });

    setTimeout(function () {
        textSpan.fadeOut(150, function () {
            textSpan.html(originalHTML).fadeIn(150);
        });
        $elem.removeClass("disabled");
    }, timeout);
}

/**
 * Copy the current page URL to the clipboard.
 *
 * @param {string} id - Hash fragment to append to the URL (optional).
 * @param {HTMLElement} elem - Button element triggering the copy action.
 */
function handleCopyURL(elem, id = "") {
    const url = new URL(window.location.href);
    if (id !== "") url.hash = `#${id}`;
    copyToClipboard(elem, url.href);
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
