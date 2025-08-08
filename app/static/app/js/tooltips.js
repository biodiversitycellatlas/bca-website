/**
 * Enable Bootstrap tooltips and popovers.
 * Also allows table HTML tags in tooltips.
 */

// Allow table elements in tooltips
bootstrap.Tooltip.Default.allowList.table = [];
bootstrap.Tooltip.Default.allowList.thead = [];
bootstrap.Tooltip.Default.allowList.tbody = [];
bootstrap.Tooltip.Default.allowList.tr = [];
bootstrap.Tooltip.Default.allowList.td = [];

const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el))

const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]')
const popoverList = [...popoverTriggerList].map(el => new bootstrap.Popover(el))
