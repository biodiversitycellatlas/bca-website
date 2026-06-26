/**
 * Gene select element.
 */

import $ from "jquery";
import TomSelect from "tom-select";

import { getViewUrl } from "../utils/urls.ts";
import { getAllLists } from "../atlas/modals/list_editor.ts";

/**
 * Display gene info in dropdown with description and domains.
 *
 * @param {object} item - Gene or gene list object.
 * @param {function} escape - Escape function from TomSelect.
 * @returns {string} HTML for dropdown option.
 */
function displayGeneInfo(item, escape) {
    if (item.group && item.group !== "genes") {
        // Display gene lists
        return `
            <div class='option'>
                ${escape(item.name)}
                <span class="text-muted small">${escape(item.gene_count)} genes</span>
            </div>
        `;
    } else {
        const domains_array = item.domains;
        let badges = "";
        for (let i = 0; i < domains_array.length; i++) {
            if (domains_array[i] !== "") {
                badges = `
                    <span class="badge rounded-pill text-bg-secondary">
                        <small>${domains_array[i]}</small>
                    </span>
                `;
            }
        }

        const desc =
            item.description === null
                ? ""
                : `
                    <span class="text-muted small">
                        ${escape(item.description)}
                    </span>`;
        return `<div class='option'>${escape(item.name)} ${desc} ${badges}</div>`;
    }
}

/**
 * Display only the gene name (and count badge for gene lists).
 *
 * @param {object} item - Gene or gene list object.
 * @param {function} escape - Escape function from TomSelect.
 * @returns {string} HTML for dropdown option.
 */
function displayGeneName(item, escape) {
    let badges = "";
    if (item.group && item.group !== "genes") {
        // Show count as a badge
        badges = `
            <span class="badge rounded-pill text-bg-secondary">
                <small>${escape(item.gene_count)}</small>
            </span>
        `;
    }
    return `<div class='option'>${escape(item.name)}${badges}</div>`;
}

/**
 * Prepend gene lists, modules and domains to TomSelect options.
 *
 * @param {string} id - Element ID prefix.
 * @param {object} select - TomSelect instance.
 * @param {function} callback - Function to call with options.
 * @param {array} data - Object with array of genes, modules, lists and domains.
 */
function prependGeneLists(id, select, callback, data) {
    const res = getAllLists(`${id}_gene_lists`)
        .concat(data.gene_lists.map((obj) => ({ ...obj, group: "preset" })))
        .concat(data.gene_modules.map((obj) => ({ ...obj, name: obj.module, group: "modules" })))
        .concat(data.domains.map((obj) => ({ ...obj, group: "domains" })))
        .concat(data.genes.map((obj) => ({ ...obj, name: obj.gene, group: "genes" })));
    callback(res);
}

/**
 * Add a default gene to select input and set it as current.
 *
 * @param {string} select - Select element.
 * @param {string} gene - Gene name.
 * @param {string} description - Gene description.
 * @param {array} domains - Array of gene domains.
 */
function setDefaultGene(select, gene, description, domains) {
    const geneOptions = { gene, description, domains };
    select.addOption(geneOptions);
    select.setValue(gene);
}

/**
 * Initialize select input with preselected genes and add optgroups.
 *
 * @param {string} select - Select element.
 * @param {string} items - Comma-separated selected genes.
 */
function initGeneSelectValues(select, items) {
    // Run only once
    let hasRun = false;
    select.on("load", function () {
        if (!hasRun && items != null && items !== "") {
            const values = items.split(",").filter((v) => v);
            if (values.length === 0) return null;

            const options = select.options;
            const missingValues = values.filter(function (value) {
                return !(value in options);
            });

            const missingValuesArray = [];
            for (const i in missingValues) {
                const elem = missingValues[i];
                missingValuesArray.push({
                    name: elem,
                    description: "",
                    domains: [],
                });
            }
            select.addOption(missingValuesArray);

            select.setValue(values);
            hasRun = true;
        }

        // Set up optgroups
        const groups = [
            ...new Set(Object.values(select.options).map((obj) => obj.group)),
        ];

        const labelMap = {
            preset: "Preset gene lists",
            custom: "Custom gene lists",
            modules: "Gene modules",
            genes: "Genes",
            domains: "Domains",
        };

        for (const group of groups) {
            if (!group) continue;
            const label = labelMap[group] || group;
            select.addOptionGroup(group, { label: label });
        }
    });
}

/**
 * Initialize the gene TomSelect element.
 *
 * @param {string} id - Element ID prefix.
 * @param {string} hash - Optional hash for URL updates.
 * @param {string} redirect - "arg" or "query" redirect mode.
 * @param {string} species - Species name.
 * @param {string} dataset - Dataset name.
 * @param {object} gene - Current gene object.
 * @param {string} selected - Preselected genes (comma-separated).
 * @param {number} limit - Maximum results to load from server.
 * @param {boolean} multiple - Allow multiple selection. If "true", also allows the user
 *     to select gene lists and domains.
 * @param {boolean} display - Toggle detailed info display.
 */
export function initGeneSelect(
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
    const select = new TomSelect(`#${id}_gene_selection`, {
        onChange: function (value) {
            // Avoid jumping if value is empty or matches current gene
            if (value !== "" && value !== gene.name) {
                if (redirect == "arg") {
                    const url = getViewUrl("atlas_gene", {
                        dataset,
                        gene: value,
                    });
                    if (window.location.pathname != url) {
                        window.location.href = url;
                    }
                } else if (redirect == "query") {
                    const url = new URL(window.location.href);
                    url.searchParams.set("gene", value);
                    if (hash !== "") url.hash = `#${hash}`;
                    window.location.href = url;
                }
            }
        },

        multiple: multiple,
        ...(multiple && { optgroupField: "group" }),

        ...(!multiple && {
            onDropdownOpen: function () {
                this.clear();
            },
            onBlur: function () {
                // Set current gene if no value is selected
                if (!this.getValue()) {
                    this.setValue(gene.name);
                }
            },
            onType: function () {
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
            // Use gene search endpoint to return gene lists, modules, and domains
            const url = getViewUrl(multiple ? "rest:genesearch-list" : "rest:gene-list");

            const q = query || gene;
            const data = { species, dataset, q, limit };

            $.ajax({url, data})
                .then((res) => {
                    if (multiple) {
                        prependGeneLists(id, this, callback, res);
                    } else {
                        const genes = res.results.map((obj) => ({ ...obj, name: obj.gene }));
                        callback(genes);
                    }
                })
                .catch((error) => {
                    console.error("Error:", error);
                    callback();
                });
        },
    });

    if (gene.name) setDefaultGene(select, gene.name, gene.description, gene.domains);
    if (multiple) initGeneSelectValues(select, selected);
    return select;
}
