/**
 * Utility functions for range sliders.
 */

function updateText(id, from_min_id, suffix="") {
    return function update(data) {
        $(id).text(data.from + suffix);

        // Update from_min of given ionRangeSlider
        if (from_min_id && from_min_id !== null) {
            $(from_min_id).data("ionRangeSlider").update({from_min: data.from})
        }
    }
}

export function initRangeSlider(selector, opts, textArgs) {
    const baseOpts = { grid: true, skin: "round" };
    const cb = updateText(...textArgs);
    $(selector).ionRangeSlider({
        ...baseOpts,
        ...opts,
        onStart: cb,
        onChange: cb,
        onUpdate: cb
    });
}
