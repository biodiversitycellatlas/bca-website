/**
 * Gene selectize element.
 */

import $ from "jquery";
import "@selectize/selectize";

/**
 * Convert a comma-separated list of numbers into ranges.
 *
 * @param {string} str - Comma-separated numeric string (e.g., "1,2,3,5").
 * @returns {string} Comma-separated ranges (e.g., "1-3,5").
 */
export function convertToRange(str) {
    // Sort numeric values
    const numbers = str
        .split(",")
        .map(Number)
        .sort((a, b) => a - b);
    let ranges = [];
    let start = numbers[0];
    let end = numbers[0];

    for (let i = 1; i < numbers.length; i++) {
        if (numbers[i] === end + 1) {
            end = numbers[i];
        } else {
            ranges.push(start === end ? `${start}` : `${start}-${end}`);
            start = numbers[i];
            end = numbers[i];
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
    let circle = `<i class="fa fa-circle color-bullet pe-1" style="color: ${color};"></i>`;
    return circle;
}

/**
 * Initialize a Selectize dropdown for metacells.
 *
 * @param {string} selected - Comma-separated pre-selected metacell values.
 * @param {string} selected2 - Alternative comma-separated pre-selected metacell values.
 */
export function initMetacellSelectize(selected, selected2) {
    $("#metacells").selectize({
        multiple: true,
        plugins: ["remove_button"],
        onInitialize: function () {
            if (selected || selected2) {
                let metacell_values = (selected || selected2).split(",");
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
                    text = escape(item.text),
                    circle = createColorCircle(escape(item.color));
                if (item.metacells) {
                    text = circle + text;
                    let metacells = convertToRange(escape(item.metacells));
                    extra = `Metacells: ${metacells}`;
                } else {
                    let type = escape(item.celltype);
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
}
