/**
 * Search bar initialization and results rendering.
 */

import TomSelect from "tom-select";

import { getViewUrl } from "../utils/urls.ts";

/**
 * Render search result options for TomSelect input.
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

        const sp = item.species_name || "";
        const words = sp.split(" ");
        const shortenedName =
            words.length > 1
                ? words
                      .map((word, index) =>
                          index === 0 ? `${word[0]}.` : word,
                      )
                      .join(" ")
                : sp;
        const species = shortenedName
            ? `
                <span class='text-muted float-end'>
                    <small><i>${shortenedName}</i></small>
                </span>`
            : "";

        res = `<div class='option'>${escape(item.name)} ${desc} ${badges} ${species}</div>`;
    } else if (group === "gene_list") {
        const count_badge =
            item.gene_count > 0
                ? `<span class="badge rounded-pill text-bg-info ms-1"><small>${item.gene_count} genes</small></span>`
                : "";
        const desc = item.description
            ? `<span class="text-muted"><small>${escape(item.description)}</small></span>`
            : "";
        res = `<div class='option'>${escape(item.name)} ${desc} ${count_badge}</div>`;
    } else if (group === "gene_module") {
        const count_badge =
            item.gene_count > 0
                ? `<span class="badge rounded-pill text-bg-info ms-1"><small>${item.gene_count} genes</small></span>`
                : "";
        const dataset_name = item.dataset
            ? `<span class="text-muted"><small>${escape(item.dataset)}</small></span>`
            : "";
        res = `<div class='option'>${escape(item.name)} ${dataset_name} ${count_badge}</div>`;
    } else if (group === "domain") {
        const count_badge =
            item.gene_count > 0
                ? `<span class="badge rounded-pill text-bg-info ms-1"><small>${item.gene_count} genes</small></span>`
                : "";
        res = `<div class='option'>${escape(item.name)} ${count_badge}</div>`;
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
 * Configures TomSelect with:
 * - Autocomplete for datasets and genes
 * - Keyboard shortcut (/) to focus the search input
 * - Redirect on selection
 */
export function initSearch() {
    const search = new TomSelect("#bca-search", {
        maxItems: 1,
        onType: function (str) {
            if (str === "") {
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
        valueField: "id",
        labelField: "id",
        searchField: [
            "gene_name",
            "species_name",
            "description",
            "domains",
            "name",
            "species",
        ],
        score: function () {
            return function () {
                return 1;
            };
        },
        render: {
            item: () => `<div>Search the BCA...</div>`,
            option: displaySearchResults,
            optgroup_header: function (data) {
                const query = this.inputValue();
                const search = getViewUrl("search");
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

            const datasetsUrl = getViewUrl("rest:dataset-list", {
                q: query,
                limit: 5,
            });
            const genesUrl = getViewUrl("rest:genesearch-list", {
                q: query,
                limit: 3,
            });

            Promise.all([
                fetch(datasetsUrl).then((res) => res.json()).catch(() => ({ results: [], count: 0 })),
                fetch(genesUrl).then((res) => res.json()).catch(() => ({})),
            ])
                .then(([dataset_data, gene_data]) => {
                    const dataset_options = dataset_data.results.map(
                        (item) => ({
                            ...item,
                            id: `dataset_${item.slug}`,
                            group: "dataset",
                            name: item.species,
                        }),
                    );

                    const gene_options = (gene_data.genes || []).map(
                        (item) => ({
                            id: `gene_${item.gene}`,
                            group: "gene",
                            name: item.gene,
                            species_name: item.species || "",
                            description: item.description,
                            domains: item.domains || [],
                        }),
                    );

                    const gene_list_options = (
                        gene_data.gene_lists || []
                    ).map((item) => ({
                        id: `gene_list_${item.name}`,
                        group: "gene_list",
                        name: item.name,
                        description: item.description,
                        gene_count: item.gene_count || 0,
                    }));

                    const gene_module_options = (
                        gene_data.gene_modules || []
                    ).map((item) => ({
                        id: `gene_module_${item.module}`,
                        group: "gene_module",
                        name: item.module,
                        dataset: item.dataset,
                        gene_count: item.gene_count || 0,
                    }));

                    const domain_options = (gene_data.domains || []).map(
                        (item) => ({
                            id: `domain_${item.name}`,
                            group: "domain",
                            name: item.name,
                            gene_count: item.gene_count || 0,
                        }),
                    );

                    this.clearOptions();
                    this.optgroups = {
                        dataset: {
                            label: "Dataset",
                            category: "datasets",
                            count: dataset_data.count,
                        },
                        gene: {
                            label: "Gene",
                            category: "genes",
                            count: gene_data.genes
                                ? gene_data.genes.length
                                : 0,
                        },
                        gene_list: {
                            label: "Gene list",
                            category: "genes",
                            count: gene_data.gene_lists
                                ? gene_data.gene_lists.length
                                : 0,
                        },
                        gene_module: {
                            label: "Gene module",
                            category: "genes",
                            count: gene_data.gene_modules
                                ? gene_data.gene_modules.length
                                : 0,
                        },
                        domain: {
                            label: "Domain",
                            category: "genes",
                            count: gene_data.domains
                                ? gene_data.domains.length
                                : 0,
                        },
                    };

                    const allOptions = [
                        ...dataset_options,
                        ...gene_options,
                        ...gene_list_options,
                        ...gene_module_options,
                        ...domain_options,
                    ];
                    callback(allOptions);
                })
                .catch((err) => {
                    console.error("Error loading data:", err);
                    callback();
                });
        },
        onChange: function (value) {
            if (!value) return;
            const item = this.options[value];

            if (item.group === "dataset") {
                const dataset = item.slug;
                window.location.href = getViewUrl("atlas", { dataset });
            } else if (item.group === "gene") {
                const gene = item.gene_name;
                const species = item.species_name;
                if (species) {
                    window.location.href = getViewUrl("gene_entry", {
                        species,
                        gene,
                    });
                }
            } else if (item.group === "gene_list") {
                window.location.href = getViewUrl("gene_list_entry", {
                    gene_list: item.name,
                });
            } else if (item.group === "gene_module") {
                const dataset = item.dataset;
                const module_name = item.module_name;
                window.location.href = getViewUrl("gene_module_entry", {
                    dataset,
                    gene_module: module_name,
                });
            } else if (item.group === "domain") {
                window.location.href = getViewUrl("domain_entry", {
                    domain: item.name,
                });
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
