/**
 * Cell type hierarchies.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-responsive-bs5";
import { phylotree } from "phylotree";

import { updateDataMenu } from "../buttons/data_dropdown.ts";
import {
    linkDomains,
    linkGeneLists,
    makeLinkGene,
    round,
    roundPercentage,
    roundSignificantDigits,
} from "./tables/utils.ts";
import { initRangeSlider } from "../utils/range_slider.ts";
import { getViewUrl, setUrlParam } from "../utils/urls.ts";
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
// Map of node name -> node color (from the API), used to colour nodes and tips.
let nodeColors = new Map();
// Highest marker count across nodes, used to scale circle radii.
let maxMarkerCount = 0;
// Map of node name -> marker tooltip state (element, DataTable, pin/drag state).
let tooltips = new Map();
// Drag state (only one tooltip is dragged at a time).
let dragging = false;
let dragTooltip = null;
// Cursor offset from the dragged tooltip's top-left.
let dragOffsetX = 0;
let dragOffsetY = 0;
// True if the current drag moved the tooltip (suppresses the trailing click).
let dragMoved = false;

/**
 * Create dendrogram plot.
 *
 * @param {string} id - Container identifier.
 * @param {string} newick - Graph tree in Newick format.
 */
function createDendrogram(id, newick, dataset) {
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
        "node-styler": (element, data) => nodeStyler(element, data, dataset),
        // Colour each edge by its target node's color (as in the phylotree
        // "colored by host" example). phylotree.css sets `.branch { stroke:
        // #999 }`, which beats presentation attributes, so use an inline
        // style with !important for the color to actually apply.
        "edge-styler": (element, d) => {
            if (!colorsEnabled()) return;
            const color = nodeColors.get(d.target.data.name) || "#AAAAAA";
            element.style("stroke", color, "important");
        },
    });

    // Force element to display
    const container = document.querySelector(containerId);
    container.style.position = "relative";
    container.innerHTML = "";
    container.appendChild(tree.display.show());

    // The edge-styler only runs in refresh(), which phylotree doesn't call on
    // render; re-apply edge colors after every render (initial + option changes).
    tree.display.on("rendered", () => tree.display.refresh());
    tree.display.refresh();

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
            currentTree = createDendrogram(treeContainerId, treeData.newick, dataset);
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

    // Keep each anchored tooltip next to its node while scrolling/resizing.
    const repositionTooltips = () => {
        for (const [name, t] of tooltips) {
            if (!t.detached && !t.el.classList.contains("d-none")) positionTooltip(name);
        }
    };
    window.addEventListener("scroll", repositionTooltips, true);
    window.addEventListener("resize", repositionTooltips);

    // Drag a tooltip by its header; it detaches from the node and the arrow hides.
    document.addEventListener("mousedown", (e) => {
        const header = e.target.closest(".marker-tooltip-header");
        if (!header || e.target.closest(".marker-tooltip-close")) return;
        const el = header.closest(".marker-tooltip");
        const t = tooltips.get(el.dataset.node);
        if (!t) return;
        e.preventDefault();
        const rect = el.getBoundingClientRect();
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;
        dragging = true;
        dragTooltip = t;
        dragMoved = false;
    });
    document.addEventListener("mousemove", (e) => {
        if (!dragging || !dragTooltip) return;
        dragMoved = true;
        dragTooltip.detached = true;
        dragTooltip.pinned = true;
        dragTooltip.el.classList.add("no-arrow");
        dragTooltip.el.style.left = `${e.clientX - dragOffsetX}px`;
        dragTooltip.el.style.top = `${e.clientY - dragOffsetY}px`;
    });
    document.addEventListener("mouseup", () => {
        dragging = false;
        dragTooltip = null;
    });

    // View option controls operate on the current tree instance and sync to the URL.
    document.getElementById("tree-type")?.addEventListener("change", (e) => {
        if (currentTree) updateTreeType(currentTree, e.target.value);
        setUrlParam("tree_type", e.target.value, "linear");
    });
    document.getElementById("align-tips")?.addEventListener("change", (e) => {
        if (currentTree) updateAlignTips(currentTree, e.target.checked);
        setUrlParam("align_tips", String(e.target.checked), "true");
    });
    document.getElementById("scale-bar")?.addEventListener("change", (e) => {
        if (currentTree) updateScaleBar(currentTree, e.target.checked);
        setUrlParam("scale_bar", String(e.target.checked), "true");
    });

    // Node/edge colors are applied by the stylers at render time, so a
    // toggle just re-renders the tree.
    document.getElementById("colors")?.addEventListener("change", (e) => {
        reRenderTree(dataset);
        setUrlParam("colors", String(e.target.checked), "true");
    });

    // Close a tooltip via its button; clicking elsewhere dismisses hover (non-pinned) ones.
    document.addEventListener("click", (e) => {
        // Ignore the click that ends a drag.
        if (dragMoved) {
            dragMoved = false;
            return;
        }
        const closeBtn = e.target.closest(".marker-tooltip-close");
        if (closeBtn) {
            closeTooltip(closeBtn.closest(".marker-tooltip").dataset.node);
            return;
        }
        const onCircle = e.target.classList?.contains("marker-count-circle");
        const onTooltip = e.target.closest?.(".marker-tooltip");
        if (!onCircle && !onTooltip) {
            for (const [name, t] of [...tooltips]) {
                if (!t.pinned) closeTooltip(name);
            }
        }
    });

    // Marker specificity slider: label updates live, tree re-renders on release.
    // The initial value is set in the template from the Django context.
    const specificityFrom = Math.max(
        0,
        Math.min(
            100,
            parseInt(document.getElementById("specificity_min").value, 10) || 0,
        ),
    );
    initRangeSlider("#specificity_min", {
        min: 0,
        max: 100,
        from: specificityFrom,
        step: 1,
        onChange: (data) => {
            document.getElementById("specificity_label").textContent =
                data.from > 0 ? `≥ ${data.from}% specific` : "All markers";
        },
        onFinish: (data) => {
            applySpecificityFilter(data.from);
            reRenderTree(dataset);
            setUrlParam("specificity_min", String(data.from), "0");
        },
    });
    if (specificityFrom > 0) {
        document.getElementById("specificity_label").textContent =
            `≥ ${specificityFrom}% specific`;
    }

    // Apply the initial specificity filter (from the URL) once the tree has loaded.
    loadTree(treeContainerId, html, dataset).then((tree) => {
        if (tree && specificityFrom > 0) {
            applySpecificityFilter(specificityFrom);
            reRenderTree(dataset);
        }
    });
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
    nodeColors = new Map();
    maxMarkerCount = 0;
    const data = currentTreeData();
    if (!data) return;
    for (const node of data.nodes) {
        const count = node.markers.length;
        markerCounts.set(node.node, count);
        nodeColors.set(node.node, node.color);
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
function nodeStyler(element, data, dataset) {
    const name = data.data.name;
    const color = nodeColors.get(name) || "#AAAAAA";
    const count = markerCounts.get(name) || 0;
    // phylotree.css styles node shapes (.node circle) with stylesheet rules,
    // which beat presentation attributes, so use inline styles with
    // !important (as in the phylotree "colored by host" example). When
    // coloring is off, apply no styles at all to fall back to the defaults.
    const colored = colorsEnabled();
    // Colour the tip label according to the node's color.
    if (!data.children) {
        const text = element.selectAll("text");
        if (colored) text.style("fill", color, "important");
    }
    // No circle for nodes without markers.
    let circles = element
        .selectAll(".marker-count-circle")
        .data(count > 0 ? [name] : [])
        .join("circle")
        .attr("class", "marker-count-circle")
        .attr("data-node-name", name)
        .attr("r", () => radiusForCount(count))
        .attr("fill-opacity", 0.35);
    if (colored) {
        circles = circles
            .style("fill", color, "important")
            .style("stroke", color, "important")
            .style("stroke-width", "1px", "important");
    }
    circles
        .style("cursor", "pointer")
        .on("mouseenter", (event, d) => {
            showTooltip(event.currentTarget, d, dataset);
        })
        .on("mouseleave", (event, d) => {
            scheduleHide(d);
        })
        .on("click", (event, d) => {
            // Ignore the click that ends a drag.
            if (dragMoved) {
                dragMoved = false;
                return;
            }
            event.stopPropagation();
            showTooltip(event.currentTarget, d, dataset);
            pinTooltip(d);
        });
}

/**
 * Get (creating if needed) the marker tooltip state for a node.
 *
 * @param {string} name - Node name.
 * @param {SVGElement} circle - The circle to anchor the tooltip to.
 * @returns {Object} The tooltip state for the node.
 */
function getOrCreateTooltip(name, circle) {
    let t = tooltips.get(name);
    if (t) {
        t.circle = circle;
        return t;
    }
    const el = document.createElement("div");
    el.className = "marker-tooltip position-fixed rounded d-none";
    el.dataset.node = name;
    const body = document.createElement("div");
    body.className = "marker-tooltip-body overflow-auto p-2 px-3 text-body";
    el.appendChild(body);
    // Keep the tooltip open (and scrollable) while the cursor is over it.
    el.addEventListener("mouseenter", () => cancelHide(name));
    el.addEventListener("mouseleave", () => scheduleHide(name));
    document.body.appendChild(el);
    t = { el, body, circle, table: null, pinned: false, detached: false, hideTimer: null };
    tooltips.set(name, t);
    return t;
}

/**
 * Show the marker tooltip for a node, anchored to its circle.
 *
 * @param {SVGElement} circle - The circle element to anchor to.
 * @param {string} name - Node name.
 */
function showTooltip(circle, name, dataset) {
    const t = getOrCreateTooltip(name, circle);
    cancelHide(name);
    // Already showing for this node: just re-anchor (its data is unchanged).
    if (!t.el.classList.contains("d-none")) {
        if (!t.detached) positionTooltip(name);
        return;
    }
    const linkGene = makeLinkGene(dataset);
    const node = currentTreeData()?.nodes.find((n) => n.node === name);
    const markers = node ? node.markers : [];

    const fragment = document
        .getElementById("marker-tooltip-template")
        .content.cloneNode(true);
    fragment.querySelector(".marker-tooltip-title").textContent = name;
    fragment.querySelector(".marker-tooltip-count").textContent =
        `${markers.length} ${markers.length === 1 ? "marker" : "markers"}`;
    if (!markers.length) {
        fragment.querySelector("table").remove();
        fragment.appendChild(document.createTextNode("No markers"));
    }

    t.body.replaceChildren(fragment);
    t.body.scrollTop = 0;
    t.el.classList.remove("d-none");

    if (t.table) {
        t.table.destroy();
        t.table = null;
    }
    if (markers.length) {
        t.table = new DataTable(t.body.querySelector("table"), {
            data: markers.map((m) => ({
                gene: m.gene,
                description: m.description,
                domains: m.domains,
                genelists: m.genelists,
                p_value: m.p_value,
                q_value: m.q_value,
                log2fc: m.avg_log2fc,
                pct1: m.pct_1,
                pct2: m.pct_2,
                specificity: Math.max(m.pct_1 - m.pct_2, 0),
            })),
            columns: [
                { data: "gene", title: "Gene", render: linkGene, className: "all" },
                { data: "description", title: "Description", orderable: false, className: "truncate all" },
                { data: "domains", title: "Domains", orderable: false, render: linkDomains, className: "truncate all" },
                { data: "genelists", title: "Gene lists", orderable: false, render: linkGeneLists, className: "truncate all" },
                { data: "p_value", title: "p-value", render: roundSignificantDigits, className: "max-mobile-p" },
                { data: "q_value", title: "q-value", render: roundSignificantDigits, className: "max-mobile-p" },
                { data: "log2fc", title: "log2 Fold-Change", render: round, className: "max-mobile-p" },
                { data: "pct1", title: "DGE % (node)", render: roundPercentage, className: "max-mobile-p" },
                { data: "pct2", title: "DGE % (sister node)", render: roundPercentage, className: "max-mobile-p" },
                { data: "specificity", title: "Specificity", render: roundPercentage, className: "all" },
            ],
            order: [[9, "desc"]],
            searching: false,
            paging: false,
            info: false,
            lengthChange: false,
            autoWidth: false,
            responsive: true,
        });
    }

    // Position after the table is rendered so the height (and arrow) are correct.
    if (!t.detached) positionTooltip(name);
}

/**
 * Position a node's tooltip next to its anchored circle, within the viewport.
 *
 * @param {string} name - Node name.
 */
function positionTooltip(name) {
    const t = tooltips.get(name);
    if (!t || !t.circle) return;
    const rect = t.circle.getBoundingClientRect();

    const offset = 12;
    const margin = 8;
    const { innerWidth } = window;

    // Show below the circle, centered on it, clamped to the viewport.
    const top = rect.bottom + offset;
    const centeredLeft = rect.left + rect.width / 2 - t.el.offsetWidth / 2;
    const left = Math.max(margin, Math.min(centeredLeft, innerWidth - t.el.offsetWidth - margin));

    // Point the arrow at the circle's center (relative to the tooltip).
    t.el.style.setProperty("--marker-tooltip-arrow", `${rect.left + rect.width / 2 - left}px`);
    t.el.style.left = `${left}px`;
    t.el.style.top = `${top}px`;
}

/**
 * Close (remove) a node's tooltip, destroying its DataTable.
 *
 * @param {string} name - Node name.
 */
function closeTooltip(name) {
    const t = tooltips.get(name);
    if (!t) return;
    clearTimeout(t.hideTimer);
    if (t.table) t.table.destroy();
    t.el.remove();
    tooltips.delete(name);
}

/**
 * Close every open tooltip.
 */
function closeAllTooltips() {
    for (const name of [...tooltips.keys()]) closeTooltip(name);
}

/**
 * Pin a node's tooltip so it stays open (dismissed only via its close button).
 *
 * @param {string} name - Node name.
 */
function pinTooltip(name) {
    const t = tooltips.get(name);
    if (!t) return;
    t.pinned = true;
    cancelHide(name);
}

/**
 * Schedule closing a node's tooltip after a short delay (skipped while pinned).
 * The delay lets the cursor move onto the tooltip to scroll it.
 *
 * @param {string} name - Node name.
 */
function scheduleHide(name) {
    const t = tooltips.get(name);
    if (!t || t.pinned || dragging) return;
    clearTimeout(t.hideTimer);
    t.hideTimer = setTimeout(() => closeTooltip(name), 150);
}

/**
 * Cancel a pending tooltip hide.
 *
 * @param {string} name - Node name.
 */
function cancelHide(name) {
    const t = tooltips.get(name);
    if (!t) return;
    clearTimeout(t.hideTimer);
}

/**
 * Whether node/edge coloring is enabled via the "Colors" view option.
 *
 * @returns {boolean} True if the tree should be colored.
 */
function colorsEnabled() {
    return document.getElementById("colors")?.checked ?? true;
}

/**
 * Re-render the tree from the cached Newick (no re-fetch) so the marker-count
 * circles are added, removed, and resized to match the current filter.
 */
function reRenderTree(dataset) {
    if (!treeData) return;
    closeAllTooltips();
    computeMarkerCounts();
    currentTree = createDendrogram(treeContainerId, treeData.newick, dataset);
    applyViewOptions(currentTree);
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
