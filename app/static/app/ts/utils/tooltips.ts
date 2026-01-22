/**
 * Enable Bootstrap tooltips and popovers.
 * Also allows table HTML tags in tooltips.
 */

import { Tooltip, Popover } from "bootstrap";

/**
 * Initialize Bootstrap tooltips and popovers across the page.
 *
 * Extends the default Bootstrap tooltip allowList to permit table elements.
 */
export function enableTooltipsAndPopovers() {
    // Allow table elements in tooltips
    Tooltip.Default.allowList = {
        ...Tooltip.Default.allowList,
        table: [],
        thead: [],
        tbody: [],
        tr: [],
        td: [],
    };

    // Enable tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
        new Tooltip(el);
    });

    // Enable popovers
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach((el) => {
        new Popover(el);
    });

}
