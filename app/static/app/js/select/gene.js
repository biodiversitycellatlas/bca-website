/**
 * Gene selectize element.
 */

/* global $ */

import { getDataPortalUrl } from "../utils/urls.js";
import { getAllLists } from "../atlas/modals/list_editor.js";

function displayGeneInfo(item, escape) {
    if (item.group && item.group !== "genes") {
        // Display gene lists
        return `<div class='option'>${item.name} <span class="text-muted small">${item.count} genes</span></div>`;
    } else {
        var domains_array = item.domains;
        let badges = "";
        for (var i = 0; i < domains_array.length; i++) {
            if (domains_array[i] !== "") {
                let span =
                    '<span class="badge rounded-pill text-bg-secondary">';
                badges += ` ${span}<small>${domains_array[i]}</small></span>`;
            }
        }

        var desc =
            item.description === null
                ? ""
                : `<span class="text-muted small">${item.description}</span>`;
        return `<div class='option'>${item.name} ${desc} ${badges}</div>`;
    }
}

function displayGeneName(item, escape) {
    let badges = "";
    if (item.group && item.group !== "genes") {
        // Show count as a badge
        badges = ` <span class="badge rounded-pill text-bg-secondary"><small>${item.count}</small></span>`;
    }
    return `<div class='option'>${item.name}${badges}</div>`;
}

function prependGeneLists(id, selectize, callback, genes, domains) {
    let res = getAllLists(`${id}_gene_lists`)
        .concat(
            domains.map((obj) => ({
                ...obj,
                count: obj.gene_count,
                group: "domains",
            })),
        )
        .concat(genes.map((obj) => ({ ...obj, group: "genes" })));
    callback(res);
}

function setDefaultGene(id, name, description, domains) {
    let geneOptions = {
        name: name,
        description: description,
        domains: domains,
    };

    let selectize = $(`#${id}_gene_selection`)[0].selectize;
    selectize.addOption(geneOptions);
    selectize.setValue(name);
}

function initGeneSelectizeValues(id, selected) {
    // Run only once
    let hasRun = false;
    let selectize = $(`#${id}_gene_selection`)[0].selectize;
    selectize.on("load", function () {
        if (!hasRun) {
            var values = selected.split(",").filter((v) => v);
            if (values.length === 0) return null;

            var options = selectize.options;
            var missingValues = values.filter(function (value) {
                return !(value in options);
            });

            var missingValuesArray = [];
            for (var i in missingValues) {
                var elem = missingValues[i];
                missingValuesArray.push({
                    name: elem,
                    description: "",
                    domains: [],
                });
            }
            selectize.addOption(missingValuesArray);

            selectize.setValue(values);
            console.log(values);
            hasRun = true;
        }

        // Set up optgroups
        const groups = [
            ...new Set(
                Object.values(selectize.options).map((obj) => obj.group),
            ),
        ];

        for (i in groups) {
            const group = groups[i];
            if (group) {
                var label = group;
                if (group == "preset") {
                    label = "Preset gene lists";
                } else if (group == "custom") {
                    label = "Custom gene lists";
                } else if (group == "genes") {
                    label = "Genes";
                } else if (group == "domains") {
                    label = "Domains";
                }
                selectize.addOptionGroup(group, { label: label });
            }
        }
    });
}

export function initGeneSelectize(
    id,
    hash,
    redirect,
    species,
    dataset,
    gene,
    selected,
    limit,
    multiple,
    display,
) {
    $(`#${id}_gene_selection`).selectize({
        onChange: function (value) {
            // Avoid jumping if value is empty or matches current gene
            if (value !== "" && value !== gene.name) {
                if (redirect == "arg") {
                    let url = getDataPortalUrl("atlas_gene", dataset, value);
                    if (window.location.pathname != url) {
                        window.location.href = url;
                    }
                } else if (redirect == "query") {
                    let url = new URL(window.location.href);
                    url.searchParams.set("gene", value);
                    if (hash !== "") url.hash = `#${hash}`;
                    window.location.href = url;
                }
            }
        },

        multiple: multiple,
        ...(multiple && { optgroupField: "group" }),

        ...(!multiple && {
            onDropdownOpen: function ($dropdown) {
                this.clear();
            },
            onBlur: function () {
                // Set current gene if no value is selected
                if (!this.getValue()) {
                    this.setValue(gene.name);
                }
            },
            onType: function (str) {
                // Clear available options to avoid selection while loading more data
                this.clearOptions();
            },
        }),

        render: {
            item: display ? displayGeneInfo : displayGeneName,
            option: displayGeneInfo,
        },
        valueField: "name",
        searchField: ["name", "description", "domains"],
        respect_word_boundaries: false,
        preload: true,
        plugins: {
            ...(multiple === "true" && { remove_button: { label: " ×" } }),
        },
        load: function (query, callback) {
            const genes = $.ajax({
                url: getDataPortalUrl("rest:gene-list"),
                data: {
                    species: species,
                    q: query || gene,
                    limit: limit,
                },
            });
            console.log("genes", genes);

            const domains = multiple
                ? $.ajax({
                      url: getDataPortalUrl("rest:domain-list"),
                      data: {
                          species: species,
                          q: query || gene,
                          limit: 10,
                          order_by_gene_count: true,
                      },
                  })
                : undefined;
            console.log("domains", genes);

            Promise.all([genes, domains])
                .then((data) => {
                    if (multiple) {
                        prependGeneLists(
                            id,
                            this,
                            callback,
                            data[0].results,
                            data[1].results,
                        );
                    } else {
                        callback(data[0].results);
                    }
                })
                .catch((error) => {
                    console.error("Error:", error);
                    callback();
                });
        },
    });
    if (gene.name)
        setDefaultGene(id, gene.name, gene.description, gene.domains);
    if (multiple) initGeneSelectizeValues(id, selected);
}
