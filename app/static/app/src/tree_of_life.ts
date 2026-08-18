/**
 * Tree of Life visualization
 */

import { phylotree } from "phylotree";
import { getViewUrl } from "./utils/urls.ts";

/** Tree of life controls to improve appearance */
const TREE_DEFAULTS = {
    fontSize: 140,
    strokeWidth: 14,
    spacing: 150,
    padding: 1800,
    maxHeight: 600,
};

/** Apply custom styles to tree elements */
function applyStyles(container, strokeWidth) {
    container.querySelectorAll(".branch, .branch-tracer").forEach((el) => {
        el.style.strokeWidth = strokeWidth + "px";
    });
}

/**
 * Create an interactive tree of life plot.
 *
 * @param {string} id - DOM element ID where the chart will be rendered
 * @param {string} file - URL or path to the Newick file
 * @param {object} opts - Options: fontSize, strokeWidth, spacing, padding, maxHeight
 */
export function createTreeOfLife(id, file, opts = {}) {
    const { fontSize, strokeWidth, spacing, padding, maxHeight } = { ...TREE_DEFAULTS, ...opts };

    fetch(file)
        .then((res) => res.text())
        .then((newick) => {
            const tree = new phylotree(newick);
            const container = document.querySelector(id);
            container.innerHTML = "";

            tree.render({
                container: id,
                "font-size": fontSize,
                "align-tips": true,
                "show-scale": false,
                zoom: false,
                reroot: false,
                responsive: true,
                brush: false,
                "is-radial": true,
                selectable: false,
                collapsible: false,
                "max-radius": 2000,
                transitions: false,
            });

            container.appendChild(tree.display.show());

            tree.display.fixed_width = [spacing, spacing * 1.5];
            tree.display.pad_width = () => padding;
            tree.display.update();

            // Enforce max height
            const svg = container.querySelector("svg");
            if (svg && maxHeight) {
                svg.style.maxHeight = maxHeight + "px";
            }
            applyStyles(container, strokeWidth);

            // Link to species entry
            container.querySelectorAll(".phylotree-node-text").forEach((el) => {
                const name = el.textContent.trim();
                if (name && name.length > 2) {
                    el.style.cursor = "pointer";
                    el.addEventListener("click", () => {
                        window.location.href = getViewUrl("species_entry", { species: name });
                    });
                }
            });

            // Layout toggle buttons
            for (const mode of ["linear", "radial", "unrooted"]) {
                const input = document.getElementById("tree_layout_" + mode);
                if (!input) continue;
                input.addEventListener("change", () => {
                    if (input.checked) {
                        tree.display.radial(mode === "radial");
                        tree.display.unrooted(mode === "unrooted");
                        tree.display.alignTips(mode === "radial");
                        tree.display.update();
                        applyStyles(container, strokeWidth);
                    }
                });
            }
        });
}

export { TREE_DEFAULTS };
