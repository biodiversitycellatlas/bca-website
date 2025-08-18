/**
 * Dataset dropdown UI selectize element.
 */

/* global $ */

function renderOption(item, escape) {
    // Display common name if different than species name
    let description = "";
    if (item.name) {
        description = `
            <span class="text-muted">
                <small>${escape(item.name)}</small>
            </span>
        `;
    }

    // Add metadata (only visible when matching user query)
    let meta_array = escape(item.meta).split(",");
    let badges = "";
    for (let i = 0; i < meta_array.length; i++) {
        let elem = meta_array[i];
        if (elem && !item.name.includes(elem) && !item.text.includes(elem)) {
            badges = `
                <span class="species-meta badge rounded-pill text-bg-secondary">
                    <small>${meta_array[i]}</small>
                </span>
            `;
        }
    }
    let img = item.image === "None" ? "" : escape(item.image);
    return `
        <div class='option'>
            <img src="${img}" style="width: 20px;">
            ${item.label} ${description}${badges}
        </div>
    `;
}

function renderItem(item, escape) {
    // Display common name if different than species name
    let description = "";
    if (item.name) {
        description = `
            <span class="text-muted">
                <small>${escape(item.name)}</small>
            </span>
        `;
    }
    return `
        <div class='option'>
            <img src="${escape(item.image)}" style="width: 20px;">
            ${item.label} ${description}
        </div>
    `;
}

/**
 * Initializes a Selectize dropdown for species selection.
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
 * @param {boolean} redirect - Redirect to selected species or not.
 * @param {boolean} optgroup_columns - Enable optgroup columns layout plugin if true.
 */
export function initSpeciesSelectize(id, species, redirect, optgroup_columns) {
    $("#species-select").selectize({
        onChange: function (value) {
            // Jump to species page upon selection
            if (redirect && value !== "" && value !== species) {
                let url = new URL(window.location.href);
                url.searchParams.set("species", value);
                window.location.href = url;
            }
        },
        onDropdownOpen: function () {
            this.clear();
            setTimeout(() => {
                if (species) {
                    let current = this.getOption(species);
                    this.setActiveOption(current);
                }
            }, 10);
        },
        onBlur: function () {
            // Set current species if no value is selected
            if (!this.getValue()) {
                this.setValue(species);
            }
        },
        onType: function (str) {
            $(".highlight")
                .closest(".species-meta")
                .css("display", "inline-block");
        },
        render: { item: renderItem, option: renderOption },
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
