/**
 * Search results page.
 *
 */

import $ from "jquery";

import { getViewUrl } from "../utils/urls.ts";
import { highlightMatch, addWordBreakOpportunities } from "../utils/utils.ts";

let state = {};

let searchStartedAt = null;
let elapsedMs = null;

let previousCountsKey = null;

/**
 * Build the results count text and append the elapsed search time.
 *
 * @param {number} count - Number of results.
 * @param {string} [suffix="result"] - Suffix to append after the count.
 * @param {number|null} [elapsed=null] - Elapsed time to append in milliseconds (null to omit).
 * @returns {string} e.g. "4 results in 0.32s".
 */
function formatResultsCount(count, suffix = "result", elapsed = null) {
    suffix += count === 1 ? "" : "s";
    const text = `${count.toLocaleString()} ${suffix}`;

    if (elapsed === null) return text;

    const seconds = (elapsed / 1000).toFixed(2);
    return `${text} in ${seconds}s`;
}

/**
 * Read search state from the current URL query parameters.
 *
 * @returns {Object} Search state with q, category, species, limit, offset.
 */
function readStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return {
        q: params.get("q") || "",
        category: params.get("category") || "",
        species: params.get("species") || "",
        limit: parseInt(params.get("limit")) || 24,
        offset: parseInt(params.get("offset")) || 0,
    };
}

/**
 * Convert the species slug in the URL to the scientific name expected by search APIs.
 */
function getSpeciesName(species) {
    const name = species.replace(/[-_]/g, " ");
    return name.charAt(0).toUpperCase() + name.slice(1);
}

/**
 * Update sidebar active states for category and limit buttons.
 */
function updateSidebar() {
    $(".category-btn").removeClass("active");
    $(`.category-btn[data-category="${state.category}"]`).addClass("active");

    $(".limit-btn").removeClass("active");
    $(`.limit-btn[data-limit="${state.limit}"]`).addClass("active");
}

/**
 * Update a URL query parameter and reload search results.
 *
 * @param {string} key - Query parameter name.
 * @param {string} value - New value (removes key if empty).
 * @returns {Promise<void>} Resolves when the updated search has rendered.
 */
export function updateQuery(key, value) {
    const params = new URLSearchParams(window.location.search);
    if (value) {
        params.set(key, value);
    } else {
        params.delete(key);
    }

    if (key !== "offset") {
        params.delete("offset");
    }
    const newUrl = "?" + params.toString();
    if (window.location.search !== newUrl) {
        history.pushState({}, "", newUrl);
    }
    state = readStateFromUrl();
    return loadSearchResults();
}

/**
 * Build a URL for a search category view, preserving the current filters.
 *
 * @param {string} category - Category value ("datasets" or "genes").
 * @returns {string} Relative URL including the category query parameter.
 */
function buildCategoryUrl(category) {
    const params = new URLSearchParams(window.location.search);
    params.set("category", category);
    params.delete("offset");
    return "?" + params.toString();
}

/**
 * Show the requested search-page views and hide all other page views.
 *
 * @param {string[]} visibleElements - Selectors for views to show.
 */
function showPageElements(visibleElements) {
    const pageElements = [
        "#loading-spinner",
        "#mockup",
        "#sidebar",
        "#summary-view",
        "#category-view",
        "#no-results-state",
        "#error-state",
        "#pagination-nav",
    ];
    $(pageElements.join(", ")).hide();
    $(visibleElements.join(", ")).show();
}

/**
 * Show loading spinner and hide all result sections.
 */
function showLoading() {
    showPageElements(["#loading-spinner", "#sidebar"]);
    $("#loading-spinner").css("display", "flex");
    $("#results_count").text("");
}

/**
 * Show empty state when no results are found.
 *
 * @param {string} query - The search query.
 */
function showEmpty(query) {
    showPageElements(["#no-results-state", "#sidebar"]);
    $("#empty-query").text(query);
    $("#results_count").text(formatResultsCount(0, "result", elapsedMs));
}

/**
 * Show error state when API calls fail.
 */
function showError() {
    showPageElements(["#error-state", "#sidebar"]);
    $("#results_count").text("Error loading results");
}

/**
 * Append a single search result card to the results container.
 *
 * @param {string} title - Main title.
 * @param {string} titleUrl - Title link URL.
 * @param {string} subtitle - Subtitle text.
 * @param {string} subtitleUrl - Subtitle link URL.
 * @param {string} description - Description text.
 * @param {string[]} badges - Badge strings.
 * @param {string} [image=""] - Image URL for the result.
 * @param {string} [container="#results"] - Container selector.
 */
function appendResult(
    title,
    titleUrl,
    subtitle,
    subtitleUrl,
    description,
    badges,
    image = "",
    container = "#results",
) {
    const template = $("#result-template");
    const $clone = $(template.html());

    let titleHtml = title;
    let subtitleHtml = subtitle;
    let descriptionHtml = description;
    const query = state.q;
    if (query) {
        titleHtml = highlightMatch(titleHtml, query);
        subtitleHtml = highlightMatch(subtitleHtml, query);
        descriptionHtml = highlightMatch(descriptionHtml, query);
        badges = badges.map((item) => highlightMatch(item, query));
    }

    titleHtml = addWordBreakOpportunities(titleHtml || "", "_/");
    subtitleHtml = addWordBreakOpportunities(subtitleHtml || "", "_/");
    descriptionHtml = addWordBreakOpportunities(descriptionHtml || "", "_/");

    $clone.find(".result-title").html(titleHtml).attr("href", titleUrl);
    $clone
        .find(".result-subtitle")
        .html(subtitleHtml)
        .attr("href", subtitleUrl);
    $clone.find(".result-description").html(descriptionHtml);

    if (image) {
        $clone
            .find(".result-image")
            .attr("src", image)
            .attr("alt", `Image of ${subtitle || title}`)
            .removeClass("d-none");
    }

    badges = badges
        .map(
            (item) =>
                `<span class="badge bg-secondary species-meta me-1">${item}</span>`,
        )
        .join(" ");
    $clone.find(".result-badges").html(badges);

    $(container).append($clone);
}

/**
 * Render pagination controls.
 *
 * @param {number} total - Total number of results.
 * @param {number} limit - Results per page.
 * @param {number} offset - Current offset.
 */
function renderPagination(total, limit, offset) {
    const totalPages = Math.ceil(total / limit);
    if (totalPages <= 1) {
        $("#pagination-nav").hide();
        return;
    }

    const currentPage = Math.floor(offset / limit) + 1;
    let html = "";

    const prevDisabled = currentPage <= 1;
    html += `<li class="page-item ${prevDisabled ? "disabled" : ""}">
        <a class="page-link" href="#" data-offset="${offset - limit}" ${prevDisabled ? 'tabindex="-1"' : ""} aria-label="Previous">
            <span aria-hidden="true">«</span>
        </a>
    </li>`;

    const maxVisible = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    const endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage + 1 < maxVisible) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageOffset = (i - 1) * limit;
        html += `<li class="page-item ${i === currentPage ? "active" : ""}">
            <a class="page-link" href="#" data-offset="${pageOffset}">${i}</a>
        </li>`;
    }

    const nextDisabled = currentPage >= totalPages;
    html += `<li class="page-item ${nextDisabled ? "disabled" : ""}">
        <a class="page-link" href="#" data-offset="${offset + limit}" ${nextDisabled ? 'tabindex="-1"' : ""} aria-label="Next">
            <span aria-hidden="true">»</span>
        </a>
    </li>`;

    $("#pagination").html(html);
    $("#pagination-nav").show();
}

/**
 * Set up delegated click handlers for pagination links.
 */
function setupPaginationHandlers() {
    $("#pagination").on("click", "a.page-link", function (e) {
        e.preventDefault();
        const offset = parseInt($(this).data("offset"));
        if (!isNaN(offset) && offset >= 0) {
            $(this)
                .closest("li")
                .addClass("active")
                .siblings()
                .removeClass("active");
            updateQuery("offset", offset.toString());
        }
    });
}

/**
 * Resolve a card spec value against an API item.
 *
 * @param {Function|string} spec - Function receiving the item, or a field name.
 * @param {Object} item - Search API item.
 * @returns {*} Resolved value (empty string for missing fields).
 */
function resolve(spec, item) {
    if (typeof spec === "function") return spec(item);
    return item?.[spec] ?? "";
}

/**
 * Build a function that maps a search API item to result-card props.
 *
 * Each spec field is either a field name (e.g. `"gene"`) or a function
 * receiving the item (e.g. for URLs). `badges` is always a function.
 *
 * @param {Object} spec - `title`, `subtitle`, `description`, `badges`, `image`, `url`.
 * @returns {Function} Card props builder for an API item.
 */
function cardProps(spec) {
    return (item) => ({
        url: resolve(spec.url, item),
        title: resolve(spec.title, item),
        subtitle: resolve(spec.subtitle, item),
        description: resolve(spec.description, item),
        badges: spec.badges ? spec.badges(item) : [],
        image: resolve(spec.image, item),
    });
}

/** "N genes" badge for entry-style results (gene lists, modules, domains). */
function geneCountBadges(item) {
    const count = item.gene_count || 0;
    return count ? [`${count.toLocaleString()} genes`] : [];
}

/**
 * Get dataset metadata badges not already shown in its title or subtitle.
 *
 * @param {Object} item - Dataset search result.
 * @returns {string[]} Metadata values to display as badges.
 */
function datasetBadges(item) {
    const title = item.dataset_html + (item.name ? ` - ${item.name}` : "");
    const subtitle = item.species_common_name || "";
    return item.species_meta
        .map((i) => i.value)
        .filter((value) => !title.includes(value) && !subtitle.includes(value));
}

const categories = {
    datasets: {
        endpoint: "rest:dataset-list",
        key: "results",
        countKey: "count",
        props: cardProps({
            title: (item) =>
                item.dataset_html + (item.name ? ` - ${item.name}` : ""),
            subtitle: "species_common_name",
            description: "species_description",
            badges: datasetBadges,
            image: "",
            url: (item) => getViewUrl("atlas", { dataset: item.slug }),
        }),
    },
    genes: {
        endpoint: "rest:genesearch-list",
        key: "genes",
        countKey: "genes_count",
        props: cardProps({
            title: "gene",
            subtitle: "species",
            description: "description",
            badges: (item) => item.domains || [],
            image: "species_image_url",
            url: (item) =>
                getViewUrl("gene_entry", {
                    species: item.species || state.species || "",
                    gene: item.gene,
                }),
        }),
    },
    gene_lists: {
        endpoint: "rest:genesearch-list",
        key: "gene_lists",
        countKey: "gene_lists_count",
        props: cardProps({
            title: "name",
            subtitle: "",
            description: "description",
            badges: geneCountBadges,
            image: "",
            url: (item) =>
                getViewUrl("gene_list_entry", { gene_list: item.name }),
        }),
    },
    gene_modules: {
        endpoint: "rest:genesearch-list",
        key: "gene_modules",
        countKey: "gene_modules_count",
        props: cardProps({
            title: "module",
            subtitle: "dataset_label",
            description: "",
            badges: geneCountBadges,
            image: "image_url",
            url: (item) =>
                getViewUrl("gene_module_entry", {
                    dataset: item.dataset,
                    gene_module: item.module,
                }),
        }),
    },
    domains: {
        endpoint: "rest:genesearch-list",
        key: "domains",
        countKey: "domains_count",
        props: cardProps({
            title: "name",
            subtitle: "",
            description: "description",
            badges: geneCountBadges,
            image: "",
            url: (item) => getViewUrl("domain_entry", { domain: item.name }),
        }),
    },
};

/**
 * Render a category's API results into cards in the given container.
 *
 * Updates the result count and pagination when rendering the main results list.
 *
 * @param {Object} data - API response containing the category's results and count.
 * @param {string} category - Category key in `categories`.
 * @param {string} [container="#results"] - Selector for the results container.
 */
function renderResults(data, category, container = "#results") {
    const { key, countKey, props } = categories[category];
    $(container).empty();
    (data[key] || []).forEach((item) => {
        const { title, url, subtitle, description, badges, image } =
            props(item);
        appendResult(
            title,
            url,
            subtitle,
            url,
            description,
            badges,
            image,
            container,
        );
    });
    if (container === "#results") {
        const totalCount = data[countKey] || 0;
        $("#results_count").text(
            formatResultsCount(totalCount, "result", elapsedMs),
        );
        renderPagination(totalCount, state.limit, state.offset);
    }
}

/**
 * Render the summary sections from dataset and gene-search API responses.
 *
 * @param {Object} datasetData - Dataset search API response.
 * @param {Object} geneData - Gene search API response.
 */
function renderSummary(datasetData, geneData) {
    for (const category of Object.keys(categories)) {
        const data = category === "datasets" ? datasetData : geneData;
        const { countKey } = categories[category];
        const $section = $(`section[data-category="${category}"]`);
        renderResults(data, category, $section.find(".summary-results"));
        $section
            .find(".summary-count")
            .text(`(${(data[countKey] || 0).toLocaleString()})`)
            .attr("href", buildCategoryUrl(category));
    }
    showPageElements(["#summary-view", "#sidebar"]);
}

/**
 * Update the sidebar result count for each category.
 *
 * @param {string} endpoint - Endpoint that produced the response.
 * @param {Object} data - API response containing per-category counts.
 */
function updateCategoryCounts(endpoint, data) {
    for (const category of Object.keys(categories)) {
        if (categories[category].endpoint !== endpoint) continue;

        const count = data[categories[category].countKey];
        if (count == null) continue;

        $(`.category-btn[data-category="${category}"] .category-count`).text(
            `(${count.toLocaleString()})`,
        );
    }
}

/**
 * Load search results from API based on current URL state.
 * Supports summary, datasets, and genes modes.
 *
 * @returns {Promise<void>} Resolves when the search has rendered.
 */
export function loadSearchResults() {
    state = readStateFromUrl();
    const { q, category, species, limit, offset } = state;

    if (!q) {
        showPageElements(["#mockup"]);
        $("#results_count").text("");
        $(".category-count").empty();
        previousCountsKey = null;
        return Promise.resolve();
    }

    // Reset counts when the query or the species change.
    const countsKey = `${q}|${species}`;
    if (countsKey !== previousCountsKey) {
        previousCountsKey = countsKey;
        $(".category-count").empty();
    }

    searchStartedAt = performance.now();
    elapsedMs = null;
    showLoading();
    updateSidebar();

    const params = { q: q, limit: limit, offset: offset };
    if (species) params.species = getSpeciesName(species);

    if (!category) {
        // Summary mode: fetch both datasets and genes (always from offset 0)
        const dsParams = { q: q, limit: Math.min(limit, 6) };
        const geneParams = { q: q, limit: 3 };
        if (species) {
            dsParams.species = getSpeciesName(species);
            geneParams.species = getSpeciesName(species);
        }

        const dsUrl = getViewUrl(categories.datasets.endpoint, dsParams);
        const gsUrl = getViewUrl(categories.genes.endpoint, geneParams);

        return Promise.all([
            fetch(dsUrl).then((r) => r.json()),
            fetch(gsUrl).then((r) => r.json()),
        ])
            .then(([datasetData, geneData]) => {
                elapsedMs = performance.now() - searchStartedAt;

                const dataFor = (name) =>
                    name === "datasets" ? datasetData : geneData;
                const hasResults = Object.keys(categories).some(
                    (name) => dataFor(name)[categories[name].key]?.length,
                );

                if (!hasResults) {
                    showEmpty(q);
                    return;
                }

                renderSummary(datasetData, geneData);

                const count = Object.keys(categories).reduce(
                    (sum, name) =>
                        sum + (dataFor(name)[categories[name].countKey] || 0),
                    0,
                );
                $("#results_count").text(
                    formatResultsCount(count, "result", elapsedMs),
                );

                updateCategoryCounts(categories.datasets.endpoint, datasetData);
                updateCategoryCounts(categories.genes.endpoint, geneData);
            })
            .catch(() => {
                showError();
            });
    } else if (categories[category]) {
        return loadCategory(category, params);
    }
    return Promise.resolve();
}

/**
 * Load a single category's results and refresh the sidebar counts.
 *
 * @param {string} category - Category key in `categories`.
 * @param {Object} params - Query parameters (q, limit, offset, species).
 */
function loadCategory(category, params) {
    const { endpoint, key } = categories[category];
    const q = state.q;

    return fetch(getViewUrl(endpoint, params))
        .then((res) => res.json())
        .then((data) => {
            elapsedMs = performance.now() - searchStartedAt;

            if (!data[key] || !data[key].length) {
                showEmpty(q);
            } else {
                showPageElements(["#category-view", "#sidebar"]);
                renderResults(data, category);
            }
            updateCategoryCounts(endpoint, data);
        })
        .catch(() => {
            showError();
        });
}

/**
 * Initialize the search page.
 *
 * Sets up event handlers and loads initial search results.
 *
 * @returns {Promise<void>} Resolves when the initial search has rendered.
 */
export function initSearchPage() {
    state = readStateFromUrl();

    $(".category-btn").on("click", function () {
        const category = $(this).data("category") || "";
        updateQuery("category", category);
    });

    $(".summary-count").on("click", function (e) {
        e.preventDefault();
        updateQuery("category", $(this).data("category"));
    });

    $(".limit-btn").on("click", function (e) {
        e.preventDefault();
        const limit = $(this).data("limit");
        updateQuery("limit", limit);
    });

    const $speciesSelect = $("#species-select-");
    $("#clear-species").on("click", function () {
        const speciesSelect = $speciesSelect[0];
        if (speciesSelect?.tomselect) {
            speciesSelect.tomselect.clear();
        } else if ($speciesSelect.length) {
            $speciesSelect.val("").trigger("change");
        } else {
            updateQuery("species", "");
        }
    });

    setupPaginationHandlers();

    if ($speciesSelect.length) {
        $speciesSelect.on("change", function () {
            const value = $(this).val() || "";
            updateQuery("species", value);
        });
    }

    $("#search-form").on("submit", function (event) {
        event.preventDefault();
        const q = event.target.q.value;
        if (q) {
            const params = new URLSearchParams(window.location.search);
            params.set("q", q);
            params.delete("offset");
            history.pushState({}, "", "?" + params.toString());
            state = readStateFromUrl();
            loadSearchResults();
        }
    });

    window.addEventListener("popstate", function () {
        state = readStateFromUrl();
        loadSearchResults();
    });

    return loadSearchResults();
}
