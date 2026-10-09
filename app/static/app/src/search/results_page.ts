/**
 * Search results page.
 *
 */

import $ from "jquery";

import { getViewUrl } from "../utils/urls.ts";
import { highlightMatch, addWordBreakOpportunities } from "../utils/utils.ts";

let state = {};

let searchStart = null;
let time = null;

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

    const time = (elapsed / 1000).toFixed(2);
    return `${text} in ${time}s`;
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
    loadSearchResults();
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
 * Show loading spinner and hide all result sections.
 */
function showLoading() {
    $("#loading-spinner").css("display", "flex");
    $("#summary-view").hide();
    $("#category-view").hide();
    $("#empty-state").hide();
    $("#error-state").hide();
    $("#results_count").text("");
}

/**
 * Show empty state when no results are found.
 *
 * @param {string} query - The search query.
 */
function showEmpty(query) {
    $("#loading-spinner").hide();
    $("#summary-view").hide();
    $("#category-view").hide();
    $("#empty-state").show();
    $("#empty-query").text(query);
    $("#pagination-nav").hide();
    $("#results_count").text(formatResultsCount(0, "result", time));
}

/**
 * Show error state when API calls fail.
 */
function showError() {
    $("#loading-spinner").hide();
    $("#summary-view").hide();
    $("#category-view").hide();
    $("#empty-state").hide();
    $("#pagination-nav").hide();
    $("#error-state").show();
    $("#results_count").text("Error loading results");
}

/**
 * Append a single search result card to the results container.
 *
 * @param {string} title - Main title.
 * @param {string} title_url - Title link URL.
 * @param {string} subtitle - Subtitle text.
 * @param {string} subtitle_url - Subtitle link URL.
 * @param {string} description - Description text.
 * @param {string[]} badges - Badge strings.
 * @param {string} [image=""] - Image URL for the result.
 * @param {string} [container="#results"] - Container selector.
 */
function appendResult(
    title,
    title_url,
    subtitle,
    subtitle_url,
    description,
    badges,
    image = "",
    container = "#results",
) {
    const template = $("#result-template");
    const $clone = $(template.html());

    let title_mod = title,
        subtitle_mod = subtitle,
        description_mod = description;

    const query = state.q;
    if (query) {
        title_mod = highlightMatch(title_mod, query);
        subtitle_mod = highlightMatch(subtitle_mod, query);
        description_mod = highlightMatch(description_mod, query);
        badges = badges.map((item) => highlightMatch(item, query));
    }

    const mods = { title_mod, subtitle_mod, description_mod };
    for (const key in mods) {
        mods[key] = addWordBreakOpportunities(mods[key] || "", "_/");
    }
    ({ title_mod, subtitle_mod, description_mod } = mods);

    $clone.find(".result-title").html(title_mod).attr("href", title_url);
    $clone
        .find(".result-subtitle")
        .html(subtitle_mod)
        .attr("href", subtitle_url);
    $clone.find(".result-description").html(description_mod);

    if (image) {
        $clone
            .find(".result-image")
            .attr("src", image)
            .attr("alt", `Image of ${subtitle || title}`)
            .removeClass("d-none");
    }

    badges = badges
        .map((item) => `<span class="badge bg-secondary species-meta me-1">${item}</span>`)
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
        suffix: "dataset",
        props: cardProps({
            title: (item) => item.dataset_html + (item.name ? ` - ${item.name}` : ""),
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
        suffix: "gene",
        props: cardProps({
            title: "gene",
            subtitle: "species",
            description: "description",
            badges: (item) => item.domains || [],
            image: "species_image_url",
            url: (item) => getViewUrl("gene_entry", { species: item.species || state.species || "", gene: item.gene }),
        }),
    },
    gene_lists: {
        endpoint: "rest:genesearch-list",
        key: "gene_lists",
        countKey: "gene_lists_count",
        suffix: "gene list",
        props: cardProps({
            title: "name",
            subtitle: "name",
            description: "description",
            badges: geneCountBadges,
            image: "",
            url: (item) => getViewUrl("gene_list_entry", { gene_list: item.name }),
        }),
    },
    gene_modules: {
        endpoint: "rest:genesearch-list",
        key: "gene_modules",
        countKey: "gene_modules_count",
        suffix: "gene module",
        props: cardProps({
            title: "module",
            subtitle: "dataset",
            description: "",
            badges: geneCountBadges,
            image: "",
            url: (item) => getViewUrl("gene_module_entry", { dataset: item.dataset, gene_module: item.module }),
        }),
    },
    domains: {
        endpoint: "rest:genesearch-list",
        key: "domains",
        countKey: "domains_count",
        suffix: "domain",
        props: cardProps({
            title: "name",
            subtitle: "name",
            description: "",
            badges: geneCountBadges,
            image: "",
            url: (item) => getViewUrl("domain_entry", { domain: item.name }),
        }),
    },
};

function renderResults(data, category, container = "#results") {
    const { key, countKey, suffix, props } = categories[category];
    $(container).empty();
    (data[key] || []).forEach((item) => {
        const { title, url, subtitle, description, badges, image } = props(item);
        appendResult(title, url, subtitle, url, description, badges, image, container);
    });
    if (container === "#results") {
        const totalCount = data[countKey] || 0;
        $("#results_count").text(
            formatResultsCount(totalCount, suffix, time)
        );
        renderPagination(totalCount, state.limit, state.offset);
    }
}

function renderSummary(datasetData, geneData) {
    for (const category of Object.keys(categories)) {
        const data = category === "datasets" ? datasetData : geneData;
        const { countKey, suffix } = categories[category];
        const $section = $(`section[data-category="${category}"]`);
        renderResults(data, category, $section.find(".summary-results"));
        $section
            .find(".summary-count")
            .text(`(${formatResultsCount(data[countKey] || 0, suffix)})`)
            .attr("href", buildCategoryUrl(category));
    }

    $("#summary-view").show();
    $("#category-view").hide();
}

/**
 * Update category count badges in sidebar.
 *
 * @param {number} datasetCount - Total dataset count.
 * @param {Object} geneData - Gene search API response with _count fields.
 */
function updateCategoryCounts(datasetCount, geneData) {
    for (const category of Object.keys(categories)) {
        const count =
            category === "datasets"
                ? datasetCount
                : geneData[categories[category].countKey];
        $(`.category-btn[data-category="${category}"] .category-count`).text(
            `(${(count || 0).toLocaleString()})`
        );
    }
}

/**
 * Load search results from API based on current URL state.
 * Supports summary, datasets, and genes modes.
 */
export function loadSearchResults() {
    state = readStateFromUrl();
    const { q, category, species, limit, offset } = state;

    if (!q) return;

    searchStart = performance.now();
    time = null;
    showLoading();
    updateSidebar();

    const params = { q: q, limit: limit, offset: offset };
    if (species) params.species = species.replace("_", " ");

    if (!category) {
        // Summary mode: fetch both datasets and genes (always from offset 0)
        const dsParams = { q: q, limit: Math.min(limit, 6) };
        const geneParams = { q: q, limit: 3 };
        if (species) {
            dsParams.species = species.replace("_", " ");
            geneParams.species = species.replace("_", " ");
        }

        const dsUrl = getViewUrl("rest:dataset-list", dsParams);
        const gsUrl = getViewUrl("rest:genesearch-list", geneParams);

        Promise.all([
            fetch(dsUrl).then((r) => r.json()),
            fetch(gsUrl).then((r) => r.json()),
        ])
            .then(([datasetData, geneData]) => {
                time = performance.now() - searchStart;
                $("#loading-spinner").hide();

                const dataFor = (name) => name === "datasets" ? datasetData : geneData;
                const hasResults = Object.keys(categories).some((name) => dataFor(name)[categories[name].key]?.length);

                if (!hasResults) {
                    showEmpty(q);
                    return;
                }

                renderSummary(datasetData, geneData);

                const count = Object.keys(categories)
                    .reduce((sum, name) => sum + (dataFor(name)[categories[name].countKey] || 0), 0);
                $("#results_count")
                    .text(formatResultsCount(count, "result", time));

                updateCategoryCounts(datasetData.count || 0, geneData);
                $("#pagination-nav").hide();
            })
            .catch(() => {
                showError();
            });
    } else if (categories[category]) {
        loadCategory(category, params);
    }
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

    fetch(getViewUrl(endpoint, params))
        .then((res) => res.json())
        .then((data) => {
            time = performance.now() - searchStart;
            $("#loading-spinner").hide();
            $("#summary-view").hide();
            $("#category-view").show();

            if (!data[key] || !data[key].length) {
                showEmpty(q);
                return;
            }
            renderResults(data, category);

            // Refresh sidebar counts using the complementary endpoint (limit 1)
            const otherEndpoint = endpoint === "rest:dataset-list" ? "rest:genesearch-list" : "rest:dataset-list";
            const countParams = { q, limit: 1 };
            const { species } = state;
            if (species) countParams.species = species.replace("_", " ");

            fetch(getViewUrl(otherEndpoint, countParams))
                .then((r) => r.json())
                .then((otherData) => {
                    const datasetCount = endpoint === "rest:dataset-list" ? data.count || 0 : otherData.count || 0;
                    const geneData = endpoint === "rest:dataset-list" ? otherData : data;
                    updateCategoryCounts(datasetCount, geneData);
                })
                .catch(() => {});
        })
        .catch(() => {
            showError();
        });
}

/**
 * Initialize the search page.
 *
 * Sets up event handlers and loads initial search results.
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

    $("#clear-species").on("click", function () {
        updateQuery("species", "");
    });

    setupPaginationHandlers();

    $(function () {
        const $speciesSelect = $("#species-select-");
        if ($speciesSelect.length) {
            let isInitial = true;
            $speciesSelect.on("change", function () {
                if (isInitial) {
                    isInitial = false;
                    return;
                }
                const value = $(this).val() || "";
                updateQuery("species", value);
            });
        }
    });

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

    loadSearchResults();
}
