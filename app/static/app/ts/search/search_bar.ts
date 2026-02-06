/**
 * Search bar initialization and results rendering.
 */

import TomSelect from "tom-select";

import { getDataPortalUrl } from "../utils/urls.ts";

/**
 * Render search result options for Selectize input.
 *
 * @param {Object} item - Search result item (gene or dataset)
 * @param {Function} escape - Function to escape HTML content
 * @returns {string} HTML string representing the search result option
 */
function displaySearchResults(item, escape) {
    const group = escape(item.group);
    let res = "";

    if (group === "gene") {
        let badges = "";
        const domains_array = item.domains;
        for (let i = 0; i < domains_array.length; i++) {
            if (domains_array[i] !== "") {
                badges += `
                    <span class="badge rounded-pill text-bg-secondary">
                        <small>${escape(domains_array[i])}</small>
                    </span>
                `;
            }
        }

        const desc =
            item.description === null
                ? ""
                : `
                    <span class="text-muted">
                        <small>${escape(item.description)}</small>
                    </span>
                `;

        const shortenedName = escape(item.species.scientific_name)
            .split(" ")
            .map((word, index) => (index === 0 ? `${word[0]}.` : word))
            .join(" ");
        const species = `
            <span class='text-muted float-end'>
                <small><img src="${escape(item.species.image_url)}" class="w-15px">
                <i>${shortenedName}</i></small>
            </span>
        `;

        res = `<div class='option'>${escape(item.name)} ${desc} ${badges} ${species}</div>`;
    } else if (group === "dataset") {
        const imgURL = escape(item.image_url || item.species_image_url);
        const img = !imgURL ? "" : `<img src="${imgURL}" class="w-25px"> `;
        const desc = !item.species_common_name
            ? ""
            : `
                <span class="text-muted">
                    <small>${escape(item.species_common_name)}</small>
                </span>
            `;

        const meta_array = item.species_meta.map((i) => escape(i.value));
        let badges = "";
        for (let i = 0; i < meta_array.length; i++) {
            const elem = meta_array[i];
            if (
                elem &&
                !item.species.includes(elem) &&
                !item.species_common_name
            ) {
                badges += `
                    <span class="species-meta badge rounded-pill text-bg-secondary">
                        <small>${elem}</small>
                    </span>
                `;
            }
        }
        const dataset_label = !item.name ? "" : `(${escape(item.name)})`;
        res = `<div class='option'>${img}<i>${escape(item.species)}</i> ${dataset_label} ${desc} ${badges}</div>`;
    }
    return res;
}

/**
 * Initialize the navbar search input.
 *
 * Configures Selectize with:
 * - Autocomplete for datasets and genes
 * - Keyboard shortcut (/) to focus the search input
 * - Redirect on selection
 */
export function initSearch() {
    const search = new TomSelect("#bca-search", {
        maxItems: 1,
        onType: function (str) {
            if (str === "") {
                // clear all options if input is cleared
                this.clearOptions();
                this.clear();
                this.close();
            }
        },
        onFocus: function () {
            this.clear();
        },
        onDropdownOpen: function () {
            this.clear();
        },
        valueField: "slug",
        labelField: "slug",
        searchField: [
            "species",
            "name",
            "description",
            "domains",
            "scientific_name",
        ],
        score: function () {
            // Avoid filtering by returning the same score to all results
            return function () {
                return 1;
            };
        },
        render: {
            item: () => `<div>Search the BCA...</div>`,
            option: displaySearchResults,
            optgroup_header: function (data) {
                const query = this.inputValue();
                const search = getDataPortalUrl("search");
                const count = `
                    <a href="${search}?q=${encodeURIComponent(query)}&category=${data.category}">
                        <span class="badge rounded-pill pt-1 background-primary">
                            ${data.count} results <i class="fa fa-circle-chevron-right"></i>
                        </span>
                    </a>`;
                return `
                    <div class="optgroup-header d-flex justify-content-between">
                        <span>${data.label} search</span>${count}
                    </div>`;
            },
        },
        load: function (query, callback) {
            if (!query.length) return callback();

            const params = new URLSearchParams({ q: query, limit: 5 });
            const datasetsURL = new URL(
                getDataPortalUrl("rest:dataset-list"),
                window.location.href,
            );
            datasetsURL.search = params;

            Promise.all([fetch(datasetsURL).then((res) => res.json())])
                .then(([dataset_data]) => {
                    const options = dataset_data.results.map((item) => ({
                        ...item,
                        group: "dataset",
                        name: item.species,
                    }));
                    this.clearOptions();
                    this.optgroups = {
                        dataset: {
                            label: "Dataset",
                            category: "dataset",
                            count: dataset_data.count,
                        },
                    };
                    callback(options);
                })
                .catch((err) => {
                    console.error("Error loading data:", err);
                    callback();
                });
        },
        onChange: function (value) {
            if (!value) return;
            const item = this.options[value];

            if (item.group === "gene") {
                const gene = item.name;
                const dataset = item.dataset.scientific_name.replace(" ", "_");
                window.location.href = getDataPortalUrl(
                    "atlas_gene",
                    dataset,
                    gene,
                );
            } else if (item.group === "dataset") {
                const dataset = item.slug;
                window.location.href = getDataPortalUrl("atlas", dataset);
            }
        },
        optgroupField: "group",
    });

    document.addEventListener("keydown", (e) => {
        if (
            e.key === "/" &&
            document.activeElement.tagName !== "INPUT" &&
            !e.ctrlKey &&
            !e.altKey
        ) {
            e.preventDefault();
            search.focus();
        }
    });
    return search;
}
