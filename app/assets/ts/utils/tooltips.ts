/**
 * Enable Bootstrap tooltips and popovers.
 * Also allows table HTML tags in tooltips.
 */

import { Popover, Tooltip } from "bootstrap";

/**
 * Initialize Bootstrap tooltips and popovers across the page.
 *
 * Extends the default Bootstrap tooltip allowList to permit table elements.
 */
export function enableTooltipsAndPopovers() {
    // Allow table elements in tooltips
    Tooltip.Default.allowList.table = [];
    Tooltip.Default.allowList.thead = [];
    Tooltip.Default.allowList.tbody = [];
    Tooltip.Default.allowList.tr = [];
    Tooltip.Default.allowList.td = [];

    const tooltipTriggerList = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]',
    );
    tooltipTriggerList.forEach((el) => new Tooltip(el));

    const popoverTriggerList = document.querySelectorAll(
        '[data-bs-toggle="popover"]',
    );
    popoverTriggerList.forEach((el) => new Popover(el));
}
