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
    const treeContainerId = `${id}-tree`;

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

    // Marker specificity slider, applied on button click.
    initRangeSlider("#specificity_min", { min: 0, max: 100, from: 0, step: 1 });
    document.getElementById("apply_specificity")?.addEventListener("click", () => {
        const value = Number(document.getElementById("specificity_min").value);
        document.getElementById("specificity_label").textContent =
            value > 0 ? `≥ ${value}% specific` : "All markers";
        applySpecificityFilter(value);
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
