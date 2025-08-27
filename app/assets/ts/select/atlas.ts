/**
 * Cell Atlas selectize element.
 */

import $ from "jquery";

/**
 * Toggles the 'plugin-optgroup_columns' class on 'atlas-select' based on the
 * current window width.
 *
 * @param {number} [width=960] - Window at which column view is toggled.
 */
export function toggleAtlasSelectColumnView(width = 960) {
    function toggleClassBasedOnWidth() {
        if ($(window).width() <= width) {
            $(".atlas-select").removeClass("plugin-optgroup_columns");
        } else {
            $(".atlas-select").addClass("plugin-optgroup_columns");
        }
    }
    toggleClassBasedOnWidth();
    $(window).resize(toggleClassBasedOnWidth);
}
