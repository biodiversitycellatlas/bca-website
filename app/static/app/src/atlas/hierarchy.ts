/**
 * Cell type hierarchies.
 */

import { phylotree } from "phylotree";
import { updateDataMenu } from "../buttons/data_dropdown.ts";
import { initRangeSlider } from "../utils/range_slider.ts";
import { getViewUrl } from "../utils/urls.ts";
import { showMessage } from "../utils/utils.ts";

// Current phylotree instance, updated on each (re)load.
let currentTree = null;
// Token so only the latest tree load renders its result (avoids stale races).
let loadToken = 0;
// Full (unfiltered) tree data from the API, fetched once.
let treeData = null;
// Tree data with markers filtered by the current specificity threshold.
let filteredTreeData = null;
// Tree container element id, set on init.
let treeContainerId = null;
// Map of node name -> number of (currently filtered) markers.
let markerCounts = new Map();
// Highest marker count across nodes, used to scale circle radii.
let maxMarkerCount = 0;
// Shared tooltip element for marker circles, created on demand.
let tooltipEl = null;
// Node name whose tooltip is pinned by a click (null = not pinned).
let pinnedNode = null;
// Pending hide timer, so the tooltip doesn't flicker when the cursor moves onto it.
let hideTimer = null;

/**
 * Create dendrogram plot.
 *
 * @param {string} id - Container identifier.
 * @param {string} newick - Graph tree in Newick format.
 */
function createDendrogram(id, newick) {
    const containerId = `#${id}`;

    const tree = new phylotree(newick);
    tree.render({
        container: containerId,
        "align-tips": true,
        "show-scale": true,
        zoom: false,
        reroot: false,
        responsive: true,
        brush: false,
        // Replace phylotree's fixed internal-node dots with marker-count circles.
        node_circle_size: () => 0,
        "node-styler": nodeStyler,
    });

    // Force element to display
    const container = document.querySelector(containerId);
    container.style.position = "relative";
    container.innerHTML = "";
    container.appendChild(tree.display.show());

    return tree;
}

/**
 * Load and render the cell type hierarchy for a dataset.
 *
 * @param {string} treeContainerId - Tree container identifier.
 * @param {string} html - Dataset HTML link.
 * @param {string} dataset - Dataset slug.
 */
function loadTree(treeContainerId, html, dataset) {
    const token = ++loadToken;
    const url = getViewUrl("rest:celltypetree-list", { dataset });
    updateDataMenu("trees", url, "Cell type hierarchy");

    return fetch(url)
        .then((response) => {
            if (!response.ok)
                throw new Error(`Request failed (${response.status}).`);
            return response.json();
        })
        .then((treesData) => {
            if (token !== loadToken) return; // a newer load superseded this one
            treeData = treesData.results[0];
            if (!treeData || !treeData.newick) {
                // No tree available for this dataset: show a message and disable the toolbar
                showMessage(treeContainerId, `No cell type hierarchy found for ${html}`);
                disableToolbar();
                currentTree = null;
                return;
            }

            computeMarkerCounts();
            currentTree = createDendrogram(treeContainerId, treeData.newick);
            applyViewOptions(currentTree);
            return currentTree;
        })
        .catch((error) => {
            if (token !== loadToken) return;
            console.error("Error fetching cell type hierarchy:", error);
            showMessage(treeContainerId, `Error loading cell type hierarchy for ${html}`);
            disableToolbar();
            currentTree = null;
        });
}

/**
 * Visualise cell type hierarchy.
 *
 * @param {string} id - Base identifier for the tree container.
 * @param {string} html - Dataset HTML link.
 * @param {string} dataset - Dataset slug.
 */
export function initCellTypeHierarchy(id, html, dataset) {
    treeContainerId = `${id}-tree`;

    // View option controls operate on the current tree instance.
    document.getElementById("tree-type")?.addEventListener("change", (e) => {
        if (currentTree) updateTreeType(currentTree, e.target.value);
    });
    document.getElementById("align-tips")?.addEventListener("change", (e) => {
        if (currentTree) updateAlignTips(currentTree, e.target.checked);
    });
    document.getElementById("scale-bar")?.addEventListener("change", (e) => {
        if (currentTree) updateScaleBar(currentTree, e.target.checked);
    });

    // Clicking outside a marker circle (or the pinned tooltip) unpins it.
    document.addEventListener("click", (e) => {
        const target = e.target;
        const onCircle = target.classList?.contains("marker-count-circle");
        const onTooltip = target.closest?.(".marker-tooltip");
        if (pinnedNode && !onCircle && !onTooltip) {
            pinnedNode = null;
            hideTooltip();
        }
    });

    // Marker specificity slider, applied on button click.
    initRangeSlider("#specificity_min", { min: 0, max: 100, from: 0, step: 1 });
    document.getElementById("apply_specificity")?.addEventListener("click", () => {
        const value = Number(document.getElementById("specificity_min").value);
        document.getElementById("specificity_label").textContent =
            value > 0 ? `≥ ${value}% specific` : "All markers";
        applySpecificityFilter(value);
        updateMarkerCircles();
    });

    loadTree(treeContainerId, html, dataset);
}

/**
 * Filter the cached markers by minimum specificity.
 *
 * @param {number} specificityMin - Minimum marker specificity (0-100).
 */
function applySpecificityFilter(specificityMin) {
    if (!treeData) return;
    filteredTreeData = {
        ...treeData,
        nodes: treeData.nodes.map((node) => ({
            ...node,
            markers: node.markers.filter(
                (m) => Math.max((m.pct_1 - m.pct_2) * 100, 0) >= specificityMin
            ),
        })),
    };
}

/**
 * Tree data reflecting the current specificity filter (unfiltered if none).
 *
 * @returns {Object|null} The tree data to use for marker counts.
 */
function currentTreeData() {
    return filteredTreeData || treeData;
}

/**
 * Recompute per-node marker counts from the current (filtered) tree data.
 */
function computeMarkerCounts() {
    markerCounts = new Map();
    maxMarkerCount = 0;
    const data = currentTreeData();
    if (!data) return;
    for (const node of data.nodes) {
        const count = node.markers.length;
        markerCounts.set(node.node, count);
        if (count > maxMarkerCount) maxMarkerCount = count;
    }
}

/**
 * Circle radius for a given marker count (area scales with count).
 *
 * @param {number} count - Number of markers.
 * @returns {number} Radius in pixels.
 */
function radiusForCount(count) {
    const minR = 2;
    const maxR = 14;
    if (maxMarkerCount <= 0) return minR;
    return minR + (maxR - minR) * Math.sqrt(count / maxMarkerCount);
}

/**
 * phylotree node styler: draw a circle at each node sized by its marker count.
 *
 * @param {Object} element - D3 selection of the node's SVG group.
 * @param {Object} data - The phylotree node.
 */
function nodeStyler(element, data) {
    const name = data.data.name;
    const count = markerCounts.get(name) || 0;
    element
        .selectAll(".marker-count-circle")
        .data([name])
        .join("circle")
        .attr("class", "marker-count-circle")
        .attr("data-node-name", name)
        .attr("r", () => radiusForCount(count))
        .attr("fill", "#4c72b0")
        .attr("fill-opacity", 0.35)
        .attr("stroke", "#4c72b0")
        .attr("stroke-width", 1)
        .style("cursor", "pointer")
        .on("mouseenter", (event, d) => {
            if (!pinnedNode) {
                cancelHide();
                showTooltip(d, event.clientX, event.clientY);
            }
        })
        .on("mousemove", (event) => {
            if (!pinnedNode) positionTooltip(event.clientX, event.clientY);
        })
        .on("mouseleave", () => {
            if (!pinnedNode) scheduleHide();
        })
        .on("click", (event, d) => {
            event.stopPropagation();
            if (pinnedNode === d) {
                pinnedNode = null;
                hideTooltip();
            } else {
                pinnedNode = d;
                showTooltip(d, event.clientX, event.clientY);
            }
        });
}

/**
 * Get (creating if needed) the shared marker tooltip element.
 *
 * @returns {HTMLElement} The tooltip element.
 */
function getTooltipEl() {
    if (!tooltipEl) {
        tooltipEl = document.createElement("div");
        tooltipEl.className = "marker-tooltip";
        // Keep the tooltip open (and scrollable) while the cursor is over it.
        tooltipEl.addEventListener("mouseenter", cancelHide);
        tooltipEl.addEventListener("mouseleave", scheduleHide);
        document.body.appendChild(tooltipEl);
    }
    return tooltipEl;
}

/**
 * Show the marker tooltip for a node near the given cursor position.
 *
 * @param {string} name - Node name.
 * @param {number} x - Cursor x (viewport).
 * @param {number} y - Cursor y (viewport).
 */
function showTooltip(name, x, y) {
    const el = getTooltipEl();
    const node = currentTreeData()?.nodes.find((n) => n.node === name);
    const genes = node ? node.markers.map((m) => m.gene) : [];
    el.innerHTML = `<strong>${name}</strong><br>${
        genes.length ? genes.join(", ") : "No markers"
    }`;
    el.style.display = "block";
    positionTooltip(x, y);
}

/**
 * Position the tooltip near the cursor, keeping it within the viewport.
 *
 * @param {number} x - Cursor x (viewport).
 * @param {number} y - Cursor y (viewport).
 */
function positionTooltip(x, y) {
    const el = getTooltipEl();
    const offset = 12;
    let left = x + offset;
    let top = y + offset;
    const { innerWidth, innerHeight } = window;
    if (left + el.offsetWidth > innerWidth) left = x - el.offsetWidth - offset;
    if (top + el.offsetHeight > innerHeight) top = y - el.offsetHeight - offset;
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
}

/**
 * Hide the tooltip (no-op while a tooltip is pinned).
 */
function hideTooltip() {
    if (pinnedNode) return;
    if (tooltipEl) tooltipEl.style.display = "none";
}

/**
 * Schedule hiding the tooltip after a short delay (skipped while pinned).
 * The delay lets the cursor move onto the tooltip to scroll it.
 */
function scheduleHide() {
    if (pinnedNode) return;
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideTooltip, 150);
}

/**
 * Cancel a pending tooltip hide.
 */
function cancelHide() {
    clearTimeout(hideTimer);
}

/**
 * Update the radii of the already-rendered marker-count circles.
 */
function updateMarkerCircles() {
    computeMarkerCounts();
    const container = document.getElementById(treeContainerId);
    if (!container) return;
    container.querySelectorAll(".marker-count-circle").forEach((circle) => {
        const name = circle.getAttribute("data-node-name");
        circle.setAttribute("r", radiusForCount(markerCounts.get(name) || 0));
    });
}

/**
 * Apply the current view option controls to a freshly rendered tree.
 *
 * @param {Object} tree - phylotree instance.
 */
function applyViewOptions(tree) {
    const treeType = document.querySelector('input[name="tree-type"]:checked');
    if (treeType) updateTreeType(tree, treeType.value);
    const alignTips = document.getElementById("align-tips");
    if (alignTips) updateAlignTips(tree, alignTips.checked);
    const scaleBar = document.getElementById("scale-bar");
    if (scaleBar) updateScaleBar(tree, scaleBar.checked);
}

/**
 * Disable the tree toolbar controls.
 */
function disableToolbar() {
    const fieldsets = document.querySelectorAll("#plot-options fieldset");
    fieldsets.forEach(fieldset => fieldset.disabled = true);
}

/**
 * Updates the tree layout mode.
 *
 * @param {Object} tree - phylotree instance.
 * @param {string} mode - Tree layout: "linear", "radial", or "unrooted".
 */
function updateTreeType(tree, mode) {
    tree.display.radial(mode === "radial");
    tree.display.unrooted(mode === "unrooted");
    tree.display.update();
}

/**
 * Toggles the alignment of tree tips.
 *
 * @param {Object} tree - phylotree instance.
 * @param {boolean} align - Align tree tips.
 */
function updateAlignTips(tree, align) {
    tree.display.alignTips(align);
    tree.display.update();
}

/**
 * Toggles the scale bar visibility.
 *
 * @param {Object} tree - phylotree instance.
 * @param {boolean} show - Display the scale bar.
 */
function updateScaleBar(tree, show) {
    tree.display.options["show-scale"] = show;
    tree.display.update();
}
