/**
 * Gene select element.
 */

import TomSelect from "tom-select";

import { getMetacellIndex } from "../utils/metacell.ts";

/**
 * Convert a comma-separated list of metacell names into ranges.
 *
 * @param {string} str - Comma-separated metacell names (e.g., "1,2,3,5").
 * @returns {string} Comma-separated ranges (e.g., "1-3,5").
 */
export function convertToRange(str) {
    // Sort metacells by their trailing number (keep full name if they don't have a trailing number)
    const values = str
        .split(",")
        .map((name) => ({ name, index: getMetacellIndex(name) }))
        .sort((a, b) => {
            if (a.index !== null && b.index !== null) {
                return a.index - b.index;
            }
            if (a.index !== null) return -1;
            if (b.index !== null) return 1;
            return a.name.localeCompare(b.name);
        })
        .map(({ name, index }) => (index !== null ? index : name));

    const ranges = [];
    let start = values[0];
    let end = values[0];

    for (let i = 1; i < values.length; i++) {
        if (typeof values[i] === "number" && values[i] === end + 1) {
            end = values[i];
        } else {
            ranges.push(start === end ? `${start}` : `${start}-${end}`);
            start = values[i];
            end = values[i];
        }
    }

    // Add the last range
    ranges.push(start === end ? `${start}` : `${start}-${end}`);

    return ranges.join(",");
}

/**
 * Create an HTML string for a colored circle icon.
 *
 * @param {string} color - CSS color string.
 * @returns {string} HTML string for a colored circle.
 */
function createColorCircle(color) {
    const circle = `<i class="fa fa-circle color-bullet pe-1" style="color: ${color};"></i>`;
    return circle;
}

/**
 * Initialize a TomSelect dropdown for metacells.
 *
 * @param {string} selected - Comma-separated preselected metacell values.
 * @param {string} selected2 - Alternative comma-separated preselected metacell values.
 */
export function initMetacellSelect(selected, selected2) {
    const select = new TomSelect("#metacells", {
        multiple: true,
        plugins: ["remove_button"],
        onInitialize: function () {
            if (selected || selected2) {
                const metacell_values = (selected || selected2).split(",");
                this.setValue(metacell_values);
            }
        },
        searchField: ["text", "celltype"],
        render: {
            item: function (item, escape) {
                let metacells,
                    text,
                    span_class = "badge rounded-pill text-bg-secondary";
                if (item.type == "metacells") {
                    metacells = escape(item.text);
                    text = "";
                } else {
                    metacells = item.metacells;
                    text = escape(item.text.replaceAll("_", " "));
                    text = createColorCircle(escape(item.color)) + text;
                    span_class += " ms-1";
                }

                let badge = "";
                if (metacells) {
                    metacells = convertToRange(escape(metacells));
                    badge = `<span class="${span_class}">${metacells}</span>`;
                }
                return `<div class='item'>${text}${badge}</div>`;
            },
            option: function (item, escape) {
                let extra = "",
                    text = escape(item.text);
                const circle = createColorCircle(escape(item.color));
                if (item.metacells) {
                    text = circle + text;
                    const metacells = convertToRange(escape(item.metacells));
                    extra = `Metacells: ${metacells}`;
                } else {
                    const type = escape(item.celltype);
                    extra = circle + type;
                }
                extra =
                    `<span class="float-end text-muted small"><small>` +
                    extra +
                    `</small></span>`;
                text = text.replaceAll("_", " ");
                return `<div class='option'>${text}${extra}</div>`;
            },
        },
    });
    return select;
}
