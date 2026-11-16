/**
 * Utility functions for range sliders.
 */

import $ from "jquery";
import "ion-rangeslider";

/**
 * Update text content and ionRangeSlider settings.
 *
 * @param {string} id - Selector for the element whose text will be updated.
 * @param {string|null} from_min_id - Selector for the ionRangeSlider to update `from_min` value. If null, skip update.
 * @param {string} [suffix=""] - Optional suffix appended to the displayed text.
 * @returns {function} - A callback function that takes a `data` object with a `from` property.
 */
function updateText(id, from_min_id, suffix = "") {
    return function update(data) {
        $(id).text(data.from + suffix);

        // Update from_min of given ionRangeSlider
        if (from_min_id && from_min_id !== null) {
            $(from_min_id)
                .data("ionRangeSlider")
                .update({ from_min: data.from });
        }
    };
}

/**
 * Initializes an ionRangeSlider on the given selector with base and custom options,
 * optionally linking text update callbacks to update the label text.
 *
 * Any `onStart`/`onChange`/`onUpdate` callbacks passed in `opts` are invoked
 * (with the slider `data`) alongside the text callback, if one is configured.
 *
 * @param {string} selector - jQuery selector for the slider element(s).
 * @param {object} opts - Custom ionRangeSlider options to override base settings.
 * @param {Array} [textArgs] - Optional array of arguments to pass to `updateText` to create callbacks.
 */
export function initRangeSlider(selector, opts, textArgs) {
    const baseOpts = { grid: true, skin: "round" };
    const textCallback = textArgs ? updateText(...textArgs) : undefined;
    const wrap = (fn) => (data) => {
        if (textCallback) textCallback(data);
        if (fn) fn(data);
    };

    const slider = $(selector);
    slider.ionRangeSlider({
        ...baseOpts,
        ...opts,
        onStart: wrap(opts.onStart),
        onChange: wrap(opts.onChange),
        onUpdate: wrap(opts.onUpdate),
    });
    return slider.data("ionRangeSlider");
}
