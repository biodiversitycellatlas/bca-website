/**
 * Cell type hierarchies.
 */

import { phylotree } from "phylotree";
import { getViewUrl } from "../utils/urls.ts";

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
 * @param {string} dataset - Dataset slug.
 */
export function initCellTypeHierarchy(id, dataset) {
    const url = getViewUrl("rest:celltypetree-list", { dataset });

    return fetch(url)
        .then((response) => {
            if (!response.ok) throw new Error(`Request failed (${response.status}).`);
            return response.json();
        })
        .then((treesData) => {
            const treeData = treesData[0];
            if (!treeData || typeof treeData.newick !== "string" || !treeData.newick) {
                throw new Error("The tree endpoint returned invalid data.");
            }

            const tree = createDendrogram(`${id}-tree`, treeData.newick);

            // Prepare interface actions
            document.getElementById("tree-type")?.addEventListener("change", (e) => {
                updateTreeType(tree, e.target.value);
            });

            document.getElementById("align-tips")?.addEventListener("change", (e) => {
                updateAlignTips(tree, e.target.checked);
            });

            document.getElementById("scale-bar")?.addEventListener("change", (e) => {
                updateScaleBar(tree, e.target.checked);
            });

            return tree;
        });
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
