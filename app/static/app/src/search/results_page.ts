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
 * @param {string} thumbnail - Image URL for thumbnail.
 */
function appendResult(
    title,
    title_url,
    subtitle,
    subtitle_url,
    description,
    badges,
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

function getDatasetItemProps(item) {
    const title = item.dataset_html + (item.name ? ` - ${item.name}` : "");
    const subtitle = item.species_common_name || "";
    const description = item.species_description;
    const badges = item.species_meta.map((i) => i.value).filter((i) => !title.includes(i) && !subtitle.includes(i));
    const url = getViewUrl("atlas", { dataset: item.slug });
    return { title, subtitle, description, badges, url };
}

function getGeneItemProps(item) {
    return {
        title: item.gene,
        subtitle: item.species || "",
        description: item.description || "",
        badges: item.domains || [],
        url: getViewUrl("gene_entry", {
            species: item.species,
            gene: item.gene,
        }),
    };
}

function renderDatasets(data, container = "#results") {
    $(container).empty();
    data.results.forEach((item) => {
        const { title, url, subtitle, description, badges } =
            getDatasetItemProps(item);
        appendResult(title, url, subtitle, url, description, badges, container);
    });
    if (container === "#results") {
        $("#results_count").text(
            formatResultsCount(data.count, "result", time)
        );
        renderPagination(data.count, state.limit, state.offset);
    }
}

function renderGenes(data, container = "#results") {
    $(container).empty();
    (data.genes || []).forEach((item) => {
        const { title, url, subtitle, description, badges } =
            getGeneItemProps(item);
        appendResult(title, url, subtitle, url, description, badges, container);
    });
    if (container === "#results") {
        const totalCount = data.genes_count || 0;
        $("#results_count").text(formatResultsCount(totalCount, "gene", time));
        renderPagination(totalCount, state.limit, state.offset);
    }
}

function renderSummary(datasetData, geneData) {
    renderDatasets(datasetData, "#summary-dataset-results");
    renderGenes(geneData, "#summary-gene-results");

    $("#summary-dataset-count").text(
        `(${formatResultsCount(datasetData.count, "dataset")})`
    );
    const totalGeneCount = (geneData.genes || []).length;
    $("#summary-gene-count").text(
        `(${formatResultsCount(totalGeneCount, "gene")})`
    );

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
    const geneCount =
        (geneData.genes_count || 0) +
        (geneData.gene_lists_count || 0) +
        (geneData.gene_modules_count || 0) +
        (geneData.domains_count || 0);

    $("#count-datasets").text(`(${(datasetCount || 0).toLocaleString()})`);
    $("#count-genes").text(`(${(geneCount || 0).toLocaleString()})`);
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

    const params = {
        q: q,
        limit: limit,
        offset: offset,
    };
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

                if (
                    (!datasetData.results || !datasetData.results.length) &&
                    (!geneData.genes || !geneData.genes.length)
                ) {
                    showEmpty(q);
                    return;
                }

                renderSummary(datasetData, geneData);

                const count =
                    (datasetData.count || 0) +
                    (geneData.genes ? geneData.genes.length : 0);
                $("#results_count").text(
                    formatResultsCount(count, "result", time)
                );

                updateCategoryCounts(datasetData.count || 0, geneData);
                $("#pagination-nav").hide();
            })
            .catch(() => {
                showError();
            });
    } else if (category === "datasets") {
        fetch(getViewUrl("rest:dataset-list", params))
            .then((res) => res.json())
            .then((data) => {
                time = performance.now() - searchStart;
                $("#loading-spinner").hide();
                $("#summary-view").hide();
                $("#category-view").show();

                if (!data.results || !data.results.length) {
                    showEmpty(q);
                    return;
                }

                renderDatasets(data);

                const geneParams = { q: q, limit: 1 };
                if (species) geneParams.species = species.replace("_", " ");
                fetch(getViewUrl("rest:genesearch-list", geneParams))
                    .then((r) => r.json())
                    .then((gd) => updateCategoryCounts(data.count || 0, gd))
                    .catch(() => {});
            })
            .catch(() => {
                showError();
            });
    } else if (category === "genes") {
        const geneParams = { q: q, limit: limit, offset: offset };
        if (species) geneParams.species = species.replace("_", " ");
        fetch(getViewUrl("rest:genesearch-list", geneParams))
            .then((res) => res.json())
            .then((data) => {
                time = performance.now() - searchStart;
                $("#loading-spinner").hide();
                $("#summary-view").hide();
                $("#category-view").show();

                const hasGenes = data.genes && data.genes.length;
                const hasOthers =
                    (data.gene_lists && data.gene_lists.length) ||
                    (data.gene_modules && data.gene_modules.length) ||
                    (data.domains && data.domains.length);

                if (!hasGenes && !hasOthers) {
                    showEmpty(q);
                    return;
                }
                renderGenes(data);

                const dsParams = { q: q, limit: 1 };
                if (species) dsParams.species = species.replace("_", " ");
                fetch(getViewUrl("rest:dataset-list", dsParams))
                    .then((r) => r.json())
                    .then((dd) => updateCategoryCounts(dd.count || 0, data))
                    .catch(() => {});
            })
            .catch(() => {
                showError();
            });
    }
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
