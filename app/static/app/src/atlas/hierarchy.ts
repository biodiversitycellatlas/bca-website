/**
 * Cell type hierarchies.
 */

import { phylotree } from "phylotree";
import TomSelect from "tom-select";

import { updateDataMenu } from "../buttons/data_dropdown.ts";
import {
    attachMarkerTooltip,
    closeTooltips,
    initMarkerTooltips,
} from "./tables/marker_tooltips.ts";
import { initRangeSlider } from "../utils/range_slider.ts";
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
    initMarkerTooltips();
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

    // Marker specificity slider
    const specificityFrom = Math.max(0, Math.min(100, getSpecificityMin()));
    initRangeSlider("#specificity_min", {
        min: 0,
        max: 100,
        from: specificityFrom,
        step: 1,
        onChange: (data) => updateSpecificityLabel(data.from),
        onFinish: (data) => {
            tree = renderTree(containerId, dataset, treeData, tree);
            setUrlParam("specificity_min", String(data.from), "0");
        },
    });

    // Focus on a subtree
    let lastFocus = "";
    const focusSelect = new TomSelect("#focus-node", {
        allowEmptyOption: true,
        // Clear the current item on open so a search can be typed directly
        onDropdownOpen: function () {
            this.clear(true);
        },
        // Restore the selection if the dropdown is closed without a pick
        onDropdownClose: function () {
            if (!this.getValue() && lastFocus) this.setValue(lastFocus, true);
        },
        onChange: (value) => {
            lastFocus = value;
            setUrlParam("focus_node", value, "");
            if (!treeData) return;
            tree = renderTree(containerId, dataset, treeData, tree);
        },
    });

    // Reset the focus to the full tree
    document.getElementById("focus-reset")?.addEventListener("click", () => {
        if (focusSelect.getValue()) focusSelect.setValue("");
    });

    // Focus on the node of a marker tooltip (dispatched by the tooltip's Focus button)
    document.addEventListener("hierarchy:focus-node", (e) => {
        const name = e.detail;
        if (focusSelect.getValue() !== name) focusSelect.setValue(name);
    });

    updateSpecificityLabel(specificityFrom);

    // Render tree
    loadTree(containerId, html, dataset).then((loaded) => {
        if (!loaded) return;
        treeData = loaded;
        tree = renderTree(containerId, dataset, treeData);
        addFocusOptions(focusSelect, tree);
    });
}

/**
 * The current minimum marker specificity (0-100) from the slider.
 *
 * @returns {number} The slider value.
 */
function getSpecificityMin() {
    return parseInt(document.getElementById("specificity_min").value, 10) || 0;
}

/**
 * Update the specificity filter label.
 *
 * @param {number} min - Minimum specificity (0-100).
 */
function updateSpecificityLabel(min) {
    const label = document.getElementById("specificity_label");
    label.textContent = min > 0 ? `≥ ${min}% specific` : "All markers";
}

/**
 * Tree data based on the specificity filter.
 *
 * @param {Object} data - The full (unfiltered) tree data.
 * @returns {Object} The tree data to use for marker counts and tooltips.
 */
function getFilteredTreeData(data) {
    const min = getSpecificityMin();
    if (!min) return data;

    return {
        ...data,
        nodes: data.nodes.map((node) => ({
            ...node,
            markers: node.markers.filter(
                (m) => Math.max((m.pct_1 - m.pct_2) * 100, 0) >= min,
            ),
        })),
    };
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

    // Hover to show, click to pin, drag the header to detach
    circles.style("cursor", "pointer").each(function () {
        attachMarkerTooltip(this, name, {
            dataset,
            markers: nodeMarkers,
            color: colors.get(name),
            isInternal: !!data.children,
        });
    });
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
 * Render the tree from the full tree data, applying the current
 * specificity filter and focused subtree.
 *
 * @param {string} containerId - Tree container element id.
 * @param {string} dataset - Dataset slug.
 * @param {Object|null} treeData - The full (unfiltered) tree data.
 * @param {Object} tree - The current tree instance, used to extract the focused subtree.
 * @returns {Object|undefined} The new tree instance, or undefined if no data has loaded.
 */
function renderTree(containerId, dataset, treeData, tree) {
    if (!treeData) return;
    closeTooltips();
    const data = getFilteredTreeData(treeData);
    const focus = document.getElementById("focus-node")?.value || "";
    const newick = focus ? getSubtreeNewick(tree, focus) : "";
    const source = newick ? { ...data, newick, rootName: focus } : data;
    const stats = computeNodeStats(source.nodes);
    const newTree = createDendrogram(
        containerId,
        source.newick,
        dataset,
        stats,
        source.rootName,
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
 * Serialise the subtree rooted at a node to Newick.
 *
 * @param {Object} tree - phylotree instance.
 * @param {string} name - Name of the subtree root.
 * @returns {string} The subtree in Newick format (empty string if the node is not found).
 */
function getSubtreeNewick(tree, name) {
    const target = tree.nodes.descendants().find((n) => n.data.name === name);
    if (!target) return "";

    // Iterative postorder traversal (parents after all of their descendants)
    const order = [];
    const stack = [[target, false]];
    while (stack.length) {
        const [node, processed] = stack.pop();
        if (processed) {
            order.push(node);
        } else {
            stack.push([node, true]);
            for (const child of [...(node.children ?? [])].reverse())
                stack.push([child, false]);
        }
    }

    // Serialize: each node's children were the last results pushed
    const newicks = [];
    for (const node of order) {
        const name = node.data.name;
        const safeName = /[()\[\];:,"]/.test(name) ? `"${name}"` : name;

        if (!node.children) {
            newicks.push(safeName);
        } else {
            const children = newicks.splice(
                newicks.length - node.children.length,
                node.children.length,
            );
            newicks.push(`(${children.join(",")})${safeName}`);
        }
    }
    return newicks.pop();
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

/**
 * Add the tree's internal nodes to the focus dropdown, restoring any URL focus.
 *
 * @param {Object} focusSelect - The focus TomSelect instance.
 * @param {Object} tree - The full (unfocused) tree instance.
 */
function addFocusOptions(focusSelect, tree) {
    for (const node of tree.nodes.descendants()) {
        // Skip leaves and the root (focusing on the root is the full tree)
        if (!node.children || node === tree.nodes) continue;
        focusSelect.addOption({ value: node.data.name, text: node.data.name });
    }
    // Restore the focused node from the URL
    const focus = new URLSearchParams(window.location.search).get("focus_node");
    if (focus && focusSelect.getOption(focus, true))
        focusSelect.setValue(focus);
}
