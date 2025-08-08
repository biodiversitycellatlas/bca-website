/**
 * Enable Bootstrap tooltips and popovers.
 * Also allows table HTML tags in tooltips.
 */

/* global bootstrap */

// tooltips.js
export function enableTooltipsAndPopovers() {
    // Allow table elements in tooltips
    bootstrap.Tooltip.Default.allowList.table = [];
    bootstrap.Tooltip.Default.allowList.thead = [];
    bootstrap.Tooltip.Default.allowList.tbody = [];
    bootstrap.Tooltip.Default.allowList.tr = [];
    bootstrap.Tooltip.Default.allowList.td = [];

    const tooltipTriggerList = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]',
    );
    tooltipTriggerList.forEach((el) => new bootstrap.Tooltip(el));

    const popoverTriggerList = document.querySelectorAll(
        '[data-bs-toggle="popover"]',
    );
    popoverTriggerList.forEach((el) => new bootstrap.Popover(el));
}

// call it immediately
enableTooltipsAndPopovers();
