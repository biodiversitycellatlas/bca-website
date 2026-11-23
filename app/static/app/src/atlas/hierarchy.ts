/**
 * Cell type hierarchies.
 */

import { phylotree } from "phylotree";

import { updateDataMenu } from "../buttons/data_dropdown.ts";
import { getViewUrl, setUrlParam } from "../utils/urls.ts";
import { showMessage } from "../utils/utils.ts";

const viewOptions = {
    "align-tips": (tree, control) => updateAlignTips(tree, control.checked),
    "scale-bar": (tree, control) => updateScaleBar(tree, control.checked),
    "tip-labels": (tree, control) => updateTipLabels(tree, control.checked),
};

/**
 * Create dendrogram plot.
 *
 * @param {string} id - Container identifier.
 * @param {string} newick - Graph tree in Newick format.
 * @param {string} dataset - Dataset slug.
 * @param {Object} stats - Node stats: { markers, colors, max }.
 * @param {string} [rootName] - Name to give the root (phylotree renames it to "root").
 */
function createDendrogram(id, newick, dataset, stats, rootName) {
    const containerId = `#${id}`;

    const tree = new phylotree(newick);
    if (rootName) tree.nodes.data.name = rootName;
    tree.render({
        container: containerId,
        "align-tips": true,
        "show-scale": true,
        "internal-names": areInternalNamesEnabled(),
        zoom: true,
        reroot: false,
        responsive: true,
        brush: false,
        selectable: false,
        "show-menu": false,
        node_circle_size: () => 0, // suppress internal nodes
        "node-styler": (element, data) =>
            styleDendrogramNodes(element, data, dataset, stats),
        "edge-styler": (element, data) =>
            styleDendrogramEdges(element, data, stats),
    });

    // Force element to display
    const container = document.querySelector(containerId);
    container.style.position = "relative";
    container.innerHTML = "";
    container.appendChild(tree.display.show());

    // Re-apply edge colors after every render
    tree.display.on("rendered", () => tree.display.refresh());
    tree.display.refresh();

    // Only zoom/pan while holding Ctrl or Cmd
    tree.display.zoomBehavior?.filter(
        (event) => event.ctrlKey || event.metaKey,
    );

    return tree;
}

/**
 * Load the cell type hierarchy for a dataset.
 *
 * @param {string} containerId - Tree container element id.
 * @param {string} html - Dataset HTML link.
 * @param {string} dataset - Dataset slug.
 * @returns {Promise<Object|null>} The tree data, or null if unavailable.
 */
function loadTree(containerId, html, dataset) {
    const url = getViewUrl("rest:celltypetree-list", { dataset });
    updateDataMenu("trees", url, "Cell type hierarchy");

    return fetch(url)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`Request failed (${response.status}).`);
            }
            return response.json();
        })
        .then((treesData) => {
            const data = treesData.results[0];
            if (!data || !data.newick) {
                // No tree available for this dataset
                showMessage(
                    containerId,
                    `No cell type hierarchy found for ${html}`,
                );
                disableToolbar();
                return null;
            }
            return data;
        })
        .catch((error) => {
            console.error("Error fetching cell type hierarchy:", error);
            showMessage(
                containerId,
                `Error loading cell type hierarchy for ${html}`,
            );
            disableToolbar();
            return null;
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
    const containerId = `${id}-tree`;
    let tree;
    let treeData;
    initViewOptionControls(() => tree);

    const colors = document.getElementById("colors");
    colors?.addEventListener("change", (e) => {
        tree = renderTree(containerId, dataset, treeData, tree);
        setUrlParam("colors", String(e.target.checked), "true");
    });

    const internalNames = document.getElementById("internal-names");
    internalNames?.addEventListener("change", (e) => {
        tree = renderTree(containerId, dataset, treeData, tree);
        setUrlParam("internal_names", String(e.target.checked), "false");
    });

    // Render tree
    loadTree(containerId, html, dataset).then((loaded) => {
        if (!loaded) return;
        treeData = loaded;
        tree = renderTree(containerId, dataset, treeData);
    });
}

/**
 * Compute node stats using the filtered tree data.
 *
 * @param {Array} nodes - The (filtered) tree data nodes.
 * @returns {Object} The node stats: { markers, colors, max }.
 */
function computeNodeStats(nodes) {
    const markers = new Map();
    const colors = new Map();
    let max = 0;

    for (const node of nodes) {
        markers.set(node.node, node.markers);
        colors.set(node.node, node.color);
        if (node.markers.length > max) max = node.markers.length;
    }
    return { markers, colors, max };
}

/**
 * Circle radius for a given marker count (area scales with count).
 *
 * @param {number} count - Number of markers.
 * @param {number} max - Largest marker count across nodes.
 * @returns {number} Radius in pixels.
 */
function getRadiusForCount(count, max) {
    const minR = 2;
    const maxR = 14;
    if (max <= 0) return minR;
    return minR + (maxR - minR) * Math.sqrt(count / max);
}

/**
 * Edge styler: colour each edge by its target node's color.
 *
 * @param {Object} element - D3 selection of the edge.
 * @param {Object} data - The phylotree edge.
 */
function styleDendrogramEdges(element, data, stats) {
    if (!areColorsEnabled()) return;
    const color = stats.colors.get(data.target.data.name) || "#AAAAAA";
    element.style("stroke", color, "important");
}

/**
 * Node styler: draw a circle at each node sized by its marker count,
 * with a solid inner circle sized by its transcription factor count.
 *
 * @param {Object} element - D3 selection of the node's SVG group.
 * @param {Object} data - The phylotree node.
 * @param {string} dataset - Dataset slug.
 */
function styleDendrogramNodes(element, data, dataset, stats) {
    const name = data.data.name;
    const { colors, markers } = stats;
    const nodeMarkers = markers.get(name) ?? [];
    const color = colors.get(name) || "#AAAAAA";
    const count = nodeMarkers.length;

    const colored = areColorsEnabled();

    // Colour the tip label according to the node's color
    if (!data.children) {
        const text = element.selectAll("text");
        if (colored) text.style("fill", color, "important");
    }

    // Restore internal labels when tip labels are off
    if (data.children && areInternalNamesEnabled()) {
        element.selectAll("text").text(name);
    }

    // Transcription factors among the filtered markers
    const tfCount = nodeMarkers.filter((m) =>
        (m.genelists ?? []).includes("Transcription factors"),
    ).length;
    const outerR = getRadiusForCount(count, stats.max);
    // TF disc area proportional to its share of the marker count
    const tfR = count > 0 ? outerR * Math.sqrt(tfCount / count) : 0;

    // Outer circle: all filtered markers (translucent); inner circle: TFs (solid)
    let circles = element
        .selectAll(".marker-count-circle")
        .data(count > 0 ? [name] : [])
        .join("circle")
        .attr("class", "marker-count-circle")
        .attr("r", outerR)
        .attr("fill-opacity", 0.35);

    let tfCircles = element
        .selectAll(".marker-tf-circle")
        .data(tfCount > 0 ? [name] : [])
        .join("circle")
        .attr("class", "marker-tf-circle")
        .attr("r", tfR)
        .style("pointer-events", "none");

    if (colored) {
        circles = circles
            .style("fill", color, "important")
            .style("stroke", color, "important")
            .style("stroke-width", "1px", "important");
        tfCircles = tfCircles.style("fill", color, "important");
    }
}

/**
 * Whether node/edge coloring is enabled via the "Colors" view option.
 *
 * @returns {boolean} True if the tree should be colored.
 */
function areColorsEnabled() {
    return document.getElementById("colors")?.checked ?? true;
}

/**
 * Whether internal node names are enabled via the "Internal names" view option.
 *
 * @returns {boolean} True if internal names should be drawn.
 */
function areInternalNamesEnabled() {
    return document.getElementById("internal-names")?.checked ?? false;
}

/**
 * Render the tree from the full tree data.
 *
 * @param {string} containerId - Tree container element id.
 * @param {string} dataset - Dataset slug.
 * @param {Object|null} treeData - The tree data.
 * @returns {Object|undefined} The new tree instance, or undefined if no data has loaded.
 */
function renderTree(containerId, dataset, treeData) {
    if (!treeData) return;
    const stats = computeNodeStats(treeData.nodes);
    const newTree = createDendrogram(
        containerId,
        treeData.newick,
        dataset,
        stats,
    );
    applyViewOptions(newTree);
    return newTree;
}

/**
 * Bind view option controls: apply values and append to URL.
 *
 * @param {Function} getTree - Returns the current tree instance (or undefined).
 */
function initViewOptionControls(getTree) {
    for (const radio of document.querySelectorAll('input[name="tree-type"]')) {
        radio.addEventListener("change", (e) => {
            const tree = getTree();
            if (tree) updateTreeType(tree, e.target.value);
            setUrlParam("tree_type", e.target.value, "linear");
        });
    }

    for (const [name, apply] of Object.entries(viewOptions)) {
        const control = document.getElementById(name);
        control?.addEventListener("change", (e) => {
            const tree = getTree();
            if (tree) apply(tree, e.target);
            setUrlParam(
                name.replace(/-/g, "_"),
                String(e.target.checked),
                "true",
            );
        });
    }
}

/**
 * Apply current view options to dendrogram.
 *
 * @param {Object} tree - phylotree instance.
 */
function applyViewOptions(tree) {
    updateTreeType(
        tree,
        document.querySelector('input[name="tree-type"]:checked')?.value ??
            "linear",
    );
    for (const [name, apply] of Object.entries(viewOptions)) {
        const control = document.getElementById(name);
        if (control) apply(tree, control);
    }
}

/**
 * Disable toolbar controls.
 */
function disableToolbar() {
    const fieldsets = document.querySelectorAll("#plot-options fieldset");
    fieldsets.forEach((fieldset) => (fieldset.disabled = true));
}

/**
 * Update tree layout mode.
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
 * Toggle tree tip alignment.
 *
 * @param {Object} tree - phylotree instance.
 * @param {boolean} align - Align tree tips.
 */
function updateAlignTips(tree, align) {
    tree.display.alignTips(align);
    tree.display.update();
}

/**
 * Toggle scale bar.
 *
 * @param {Object} tree - phylotree instance.
 * @param {boolean} show - Display the scale bar.
 */
function updateScaleBar(tree, show) {
    tree.display.options["show-scale"] = show;
    tree.display.update();
}

/**
 * Toggle tip name visibility.
 *
 * @param {Object} tree - phylotree instance.
 * @param {boolean} show - Show tip names.
 */
function updateTipLabels(tree, show) {
    tree.display.options["show-labels"] = show;
    tree.display.update();
}
