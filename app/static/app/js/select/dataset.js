/**
 * Dataset dropdown UI selectize element.
 */

import { getDataPortalUrl } from "../utils/urls.js";

/* global $ */

/**
 * Initializes a Selectize dropdown for dataset selection.
 *
 * Features:
 * - By default, redirects to a new dataset page on selection.
 * - Renders items and options with metadata and images.
 * - Highlights matching dataset in dropdown when opened.
 * - Resets selection to current dataset if dropdown loses focus without a value.
 *
 * @param {string} id - Unique identifier suffix for the dataset select element (DOM id format: `dataset-select-{id}`).
 * @param {string} dataset - Currently active dataset name.
 * @param {string} query - Current query parameter value for dataset (used when `redirect` is `"query"`).
 * @param {string} redirect - Determines selection behavior:
 *   "arg"   : redirect to dataset page via atlas URL.
 *   "query" : update `dataset` query parameter in current URL.
 * @param {boolean} optgroup_columns - Enable optgroup columns layout plugin if true.
 */
export function initDatasetSelectize(
    id,
    dataset,
    query,
    redirect,
    optgroup_columns,
) {
    let $select = $(`#dataset-select-${id}`);
    $select.selectize({
        onChange: function (value) {
            // Jump to dataset page upon selection
            if (redirect == "arg") {
                if (value !== "" && value !== dataset) {
                    // Avoid jumping if value is empty or matches current dataset
                    window.location.href = getDataPortalUrl("atlas", value);
                }
            } else if (redirect == "query") {
                if (value !== "" && value !== query) {
                    let url = new URL(window.location.href);
                    url.searchParams.set("dataset", value);
                    window.location.href = url;
                }
            }
        },
        onDropdownOpen: function () {
            this.clear();
            setTimeout(() => {
                dataset = redirect == "query" ? query : dataset;
                if (dataset) {
                    let current = this.getOption(dataset);
                    this.setActiveOption(current);
                }
            }, 10);
        },
        onBlur: function () {
            // Set current dataset if no value is selected
            if (!this.getValue()) {
                this.setValue(redirect == "query" ? query : dataset);
            }
        },
        onType: function (str) {
            $(".highlight")
                .closest(".species-meta")
                .css("display", "inline-block");
        },
        render: {
            item: function (item, escape) {
                // Display common name if different than dataset name
                let description = "";
                if (item.name) {
                    description = `
                        <span class="text-muted">
                            <small>${escape(item.name)}</small>
                        </span>
                    `;
                }
                let dataset = !item.dataset ? "" : `(${escape(item.dataset)})`;
                return `
                    <div class='option'>
                        <span class="text-muted small">
                            ${redirect !== "query" ? "Dataset:" : ""}
                        </span>
                        <img src="${escape(item.image)}" class="w-20px">
                        ${item.label} ${description}
                    </div>`;
            },
            option: function (item, escape) {
                // Display common name if different than dataset name
                let description = "";
                if (item.name !== item.text) {
                    description = `
                        <span class="text-muted">
                            <small>${escape(item.name)}</small>
                        </span>
                    `;
                }

                // Add metadata (only visible when matching user query)
                let meta_array = item.meta.split(",");

                let badges = "";
                for (let i = 0; i < meta_array.length; i++) {
                    let elem = meta_array[i];
                    if (
                        elem &&
                        !item.name.includes(elem) &&
                        !item.text.includes(elem)
                    ) {
                        let span =
                            '<span class="species-meta badge rounded-pill text-bg-secondary">';
                        badges += ` ${span}<small>${meta_array[i]}</small></span>`;
                    }
                }
                let dataset = !item.dataset ? "" : `(${escape(item.dataset)})`;
                let img = item.image === "None" ? "" : escape(item.image);
                return `<div class='option'>
                    <img src="${img}" class="w-20px">
                    ${item.label}${description}${badges}
                </div>`;
            },
        },
        searchField: ["text", "meta", "optgroup", "name"],
        plugins: {
            ...(optgroup_columns && {
                optgroup_columns: {
                    equalizeWidth: false,
                    equalizeHeight: false,
                },
            }),
        },
    });
}
