/* global $ */
import { displaySearchResults } from "./dropdown.js";

export function initSearch({ urls }) {
    $("#bca-search").selectize({
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
                let query = this.getTextboxValue();
                let count = `<a href="${urls.search}?q=${encodeURIComponent(query)}&category=${data.category}"><span class="badge rounded-pill pt-1 background-primary">${data.count} results <i class="fa fa-circle-chevron-right"></i></span></a>`;
                return `<div class="optgroup-header d-flex justify-content-between"><span>${data.label} search</span>${count}</div>`;
            },
        },
        load: function (query, callback) {
            if (!query.length) return callback();

            let params = new URLSearchParams({ q: query, limit: 5 });
            let datasetsURL = new URL(urls.datasetList, window.location.href);
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
                    console.log(options);
                    callback(options);
                })
                .catch((err) => {
                    console.error("Error loading data:", err);
                    callback();
                });
        },
        onChange: function (value) {
            if (!value) return;
            let item = this.options[value];

            if (item.group === "gene") {
                let gene = item.name;
                let dataset = item.dataset.scientific_name.replace(" ", "_");
                window.location.href = urls.atlasGene
                    .replace("dataset_placeholder", dataset)
                    .replace("gene_placeholder", gene);
            } else if (item.group === "dataset") {
                let dataset = item.slug;
                window.location.href = urls.atlasView.replace(
                    "dataset_placeholder",
                    dataset,
                );
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
            $("#bca-search")[0].selectize.focus();
        }
    });
}
