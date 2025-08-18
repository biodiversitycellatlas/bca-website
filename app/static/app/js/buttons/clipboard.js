/**
 * Clipboard functions.
 */

/* global $ */

function handleCopyURL(id, elem) {
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

export function initClipboardButton(id) {
    $(`#clipboard_${id}`).on("click", function () {
        handleCopyURL(id, this);
    });
}
