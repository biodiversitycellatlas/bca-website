/**
 * Cell type hierarchies.
 */

import { phylotree } from "phylotree";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { getViewUrl } from "../utils/urls.ts";
import { showMessage } from "../utils/utils.ts";

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
 * Visualise cell type hierarchy.
 *
 * @param {string} id - Base identifier for the tree container.
 * @param {string} html - Dataset HTML link.
 * @param {string} dataset - Dataset slug.
 */
export function initCellTypeHierarchy(id, html, dataset) {
    const url = getViewUrl("rest:celltypetree-list", { dataset });
    appendDataMenu("trees", url, "Cell type hierarchy");
    const treeContainerId = `${id}-tree`;

    return fetch(url)
        .then((response) => {
            if (!response.ok)
                throw new Error(`Request failed (${response.status}).`);
            return response.json();
        })
        .then((treesData) => {
            const treeData = treesData.results[0];
            if (!treeData || !treeData.newick) {
                // No tree available for this dataset: show a message and disable the toolbar
                showMessage(treeContainerId, `No cell type hierarchy found for ${html}`);
                disableToolbar();
                return;
            }

            const tree = createDendrogram(treeContainerId, treeData.newick);

            // Prepare interface actions
            const treeType = document.getElementById("tree-type");
            treeType?.addEventListener("change", (e) => updateTreeType(tree, e.target.value));

            const alignTips = document.getElementById("align-tips");
            alignTips?.addEventListener("change", (e) => updateAlignTips(tree, e.target.checked));

            const scaleBar = document.getElementById("scale-bar");
            scaleBar?.addEventListener("change", (e) => updateScaleBar(tree, e.target.checked));

            return tree;
        });
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
