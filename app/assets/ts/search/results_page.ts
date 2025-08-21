/**
 * Search results page.
 *
 */

import $ from "jquery";

import { getDataPortalUrl } from "../utils/urls.js";
import { highlightMatch, addWordBreakOpportunities } from "../utils/utils.js";

/**
 * Update the URL query parameter.
 *
 * @param {string} key - Query parameter name.
 * @param {string} value - New value (removes if empty).
 */
export function updateQuery(key, value) {
    let searchParams = new URLSearchParams(window.location.search);
    if (value) {
        searchParams.set(key, value);
    } else {
        searchParams.delete(key);
    }

    let searchString = "?" + searchParams.toString();
    if (window.location.search != searchString) {
        window.location.search = searchString;
    }
}

/**
 * Append a search result to the results container.
 *
 * @param {string} title - Main title of the result.
 * @param {string} title_url - URL for the title link.
 * @param {string} subtitle - Subtitle text.
 * @param {string} subtitle_url - URL for the subtitle link.
 * @param {string} description - Description text.
 * @param {array} badges - Array of badge strings.
 */
function appendResult(
    title,
    title_url,
    subtitle,
    subtitle_url,
    description,
    badges,
) {
    const template = $("#result-template");
    const container = $("#results");
    let $clone = $(template.html());

    let title_mod = title,
        subtitle_mod = subtitle,
        description_mod = description;

    // Highlight query matches
    let query = $("#search").val().trim();
    if (query) {
        title_mod = highlightMatch(title_mod, query);
        subtitle_mod = highlightMatch(subtitle_mod, query);
        description_mod = highlightMatch(description_mod, query);
        badges = badges.map((item) => highlightMatch(item, query));
    }

    // Add word break lines on underscores
    const mods = { title_mod, subtitle_mod, description_mod };
    for (const key in mods) {
        // Regex: ignore HTML code, i.e. text inside brackets <>
        mods[key] = addWordBreakOpportunities(mods[key] || "", "_/");
    }
    ({ title_mod, subtitle_mod, description_mod } = mods);

    $clone.find(".result-title").html(title_mod).attr("href", title_url);
    $clone
        .find(".result-subtitle")
        .html(subtitle_mod)
        .attr("href", subtitle_url);
    $clone.find(".result-description").html(description_mod);

    badges = badges
        .map(
            (item) =>
                `<span class="badge bg-secondary species-meta">${item}</span>`,
        )
        .join(" ");
    $clone.find(".result-badges").html(badges);

    container.append($clone);
}

/**
 * Load search results from API and display them.
 * Supports datasets and genes.
 *
 * @param {string} species - Species filter.
 * @param {string} query - Search query.
 * @param {number} limit - Max number of results.
 * @param {number} offset - Pagination offset.
 * @param {string} category - "datasets" or "genes".
 */
export function loadSearchResults(
    species,
    query = "",
    limit = 12,
    offset = 0,
    category = "datasets",
) {
    // Fetch data from API
    let params = new URLSearchParams({
        q: encodeURIComponent(query),
        limit: limit,
        offset: offset,
        species: species.replace("_", " "),
    });

    if (category === "datasets") {
        let datasetsURL = new URL(
            getDataPortalUrl("rest:dataset-list"),
            window.location.href,
        );
        datasetsURL.search = params;

        fetch(datasetsURL)
            .then((res) => res.json())
            .then((data) => {
                data.results.forEach((item) => {
                    let title = `${item.dataset_html}`;
                    if (item.name) {
                        title = `${title} - ${item.name}`;
                    }
                    let subtitle = item.species_common_name || "";

                    let description = item.species_description;
                    let badges = item.species_meta
                        .map((item) => item.value)
                        .filter(
                            (item) =>
                                !title.includes(item) &&
                                !subtitle.includes(item),
                        );

                    let dataset_url = getDataPortalUrl("atlas", item.slug);
                    appendResult(
                        title,
                        dataset_url,
                        subtitle,
                        dataset_url,
                        description,
                        badges,
                    );
                });
                $("#results_count").text(
                    `${data.count.toLocaleString()} results`,
                );
            })
            .catch((err) => {
                console.error("Error loading data:", err);
            });
    } else if (category === "genes") {
        let genesURL = new URL(
            getDataPortalUrl("gene_list"),
            window.location.href,
        );
        genesURL.search = params;

        fetch(genesURL)
            .then((res) => res.json())
            .then((data) => {
                data.results.forEach((item) => {
                    let gene = item.name;
                    let species_name = item.species
                        ? item.species.scientific_name
                        : "";
                    let description = item.description;
                    let domains = item.domains;

                    let slug = item.species
                        ? item.species.scientific_name.slug
                        : species.slug;
                    let species_url = getDataPortalUrl("atlas", slug);
                    let gene_url = getDataPortalUrl("atlas_gene", slug, gene);
                    appendResult(
                        gene,
                        gene_url,
                        species_name,
                        species_url,
                        description,
                        domains,
                    );
                });
                $("#results_count").text(
                    `${data.count.toLocaleString()} results`,
                );
            })
            .catch((err) => {
                console.error("Error loading data:", err);
            });
    }
}

/**
 * Update query param and reload results when submitting form.
 */
export function initFormHandler() {
    // Modify form before submission to only modify query
    $("form").on("submit", function (event) {
        event.preventDefault();
        updateQuery("q", event.target.q.value);
    });
}
