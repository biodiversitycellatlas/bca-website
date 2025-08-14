/**
 * Gene selectize element.
 */

/* global $ */

function convertToRange(str) {
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

export function initMetacellSelectize(selected, selected2) {
    $("#metacells").selectize({
        multiple: true,
        plugins: ["remove_button"],
        onInitialize: function () {
            if (selected || selected2) {
                var metacell_values = (selected || selected2).split(",");
                this.setValue(metacell_values);
            }
        },
        searchField: ["text", "celltype"],
        render: {
            item: function (item, escape) {
                var metacells;
                var text;
                var span_class = "badge rounded-pill text-bg-secondary";
                if (item.type == "metacells") {
                    metacells = item.text;
                    text = "";
                } else {
                    metacells = item.metacells;
                    text = item.text.replaceAll("_", " ");
                    span_class += " ms-1";
                }

                var badge = "";
                if (metacells) {
                    metacells = convertToRange(String(metacells));
                    badge = `<span class="${span_class}">${metacells}</span>`;
                }
                return `<div class='item'>${text}${badge}</div>`;
            },
            option: function (item, escape) {
                var extra = "";
                var text = item.text;
                var circle = `<i class="fa fa-circle color-bullet" style="color: ${item.color};"></i> `;
                if (item.metacells) {
                    text = circle + text;
                    var metacells = convertToRange(String(item.metacells));
                    extra = `Metacells: ${metacells}`;
                } else {
                    var type = item.celltype;
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
