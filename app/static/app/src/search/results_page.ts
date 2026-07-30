/**
 * Search results page.
 *
 */

import $ from "jquery";

import { getViewUrl } from "../utils/urls.ts";
import { highlightMatch, addWordBreakOpportunities } from "../utils/utils.ts";

let state = {};

function readStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return {
        q: params.get("q") || "",
        category: params.get("category") || "",
        species: params.get("species") || "",
        limit: parseInt(params.get("limit")) || 12,
        offset: parseInt(params.get("offset")) || 0,
    };
}

function updateSidebar() {
    $(".category-btn").removeClass("active");
    $(`.category-btn[data-category="${state.category}"]`).addClass("active");

    $(".limit-btn").removeClass("active");
    $(`.limit-btn[data-limit="${state.limit}"]`).addClass("active");
}

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

function showLoading() {
    $("#loading-spinner").show();
    $("#summary-view").hide();
    $("#category-view").hide();
    $("#empty-state").hide();
    $("#pagination-nav").hide();
    $("#error-state").hide();
    $("#results_count").text("");
}

function showEmpty(query) {
    $("#loading-spinner").hide();
    $("#summary-view").hide();
    $("#category-view").hide();
    $("#empty-state").show();
    $("#empty-query").text(query);
    $("#pagination-nav").hide();
    $("#results_count").text("0 results");
}

function showError() {
    $("#loading-spinner").hide();
    $("#summary-view").hide();
    $("#category-view").hide();
    $("#empty-state").hide();
    $("#pagination-nav").hide();
    $("#error-state").show();
    $("#results_count").text("Error loading results");
}

function appendResult(title, title_url, subtitle, subtitle_url, description, badges, thumbnail) {
    const template = $("#result-template");
    const container = $("#results");
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
    $clone.find(".result-subtitle").html(subtitle_mod).attr("href", subtitle_url);
    $clone.find(".result-description").html(description_mod);

    if (thumbnail) {
        $clone.find(".result-thumbnail").html(`<img src="${thumbnail}" class="rounded" style="width:32px;height:32px;object-fit:cover;">`);
    }

    badges = badges
        .map((item) => `<span class="badge bg-secondary species-meta me-1">${item}</span>`)
        .join(" ");
    $clone.find(".result-badges").html(badges);

    container.append($clone);
}

function appendSummaryResult(containerId, title, url, subtitle, description, badges, thumbnail) {
    const container = $(`#${containerId}`);
    const html = `
        <div class="col mb-2">
            <div class="card h-100">
                <div class="card-body py-2 px-3">
                    <div class="d-flex align-items-start mb-1">
                        ${thumbnail ? `<span class="me-2 flex-shrink-0"><img src="${thumbnail}" class="rounded" style="width:32px;height:32px;object-fit:cover;"></span>` : ""}
                        <div class="min-width-0">
                            <a href="${url}" class="fw-semibold small stretched-link">${title}</a>
                            ${subtitle ? `<span class="text-secondary small d-block">${subtitle}</span>` : ""}
                        </div>
                    </div>
                    ${description ? `<p class="card-text small truncate-3 mb-1 text-muted">${description}</p>` : ""}
                    ${badges.length ? `<div>${badges.map(b => `<span class="badge bg-secondary species-meta me-1">${b}</span>`).join(" ")}</div>` : ""}
                </div>
            </div>
        </div>
    `;
    container.append(html);
}

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
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
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

function setupPaginationHandlers() {
    $("#pagination").on("click", "a.page-link", function (e) {
        e.preventDefault();
        const offset = parseInt($(this).data("offset"));
        if (!isNaN(offset) && offset >= 0) {
            updateQuery("offset", offset.toString());
        }
    });
}

function renderDatasets(data) {
    const container = $("#results");
    container.empty();

    data.results.forEach((item) => {
        let title = `${item.dataset_html}`;
        if (item.name) {
            title = `${title} - ${item.name}`;
        }
        const subtitle = item.species_common_name || "";
        const description = item.species_description;
        const badges = item.species_meta
            .map((item) => item.value)
            .filter((item) => !title.includes(item) && !subtitle.includes(item));
        const thumbnail = item.image_url || item.species_image_url || "";
        const dataset_url = getViewUrl("atlas", { dataset: item.slug });
        appendResult(title, dataset_url, subtitle, dataset_url, description, badges, thumbnail);
    });

    $("#results_count").text(`${data.count.toLocaleString()} results`);
    renderPagination(data.count, state.limit, state.offset);
}

function renderGeneGeneList(data) {
    const container = $("#results");
    container.empty();

    const items = data.genes || [];
    items.forEach((item) => {
        const gene = item.gene;
        const species_name = item.species || "";
        const description = item.description || "";
        const domains = item.domains || [];
        const species_url = "";
        const gene_url = getViewUrl("gene_entry", { species: species_name, gene });
        appendResult(gene, gene_url, species_name, species_url, description, domains, "");
    });

    const totalCount = data.genes_count || items.length;
    const otherCounts = [];
    if (data.gene_lists && data.gene_lists.length) otherCounts.push(`${data.gene_lists.length} gene lists`);
    if (data.gene_modules && data.gene_modules.length) otherCounts.push(`${data.gene_modules.length} modules`);
    if (data.domains && data.domains.length) otherCounts.push(`${data.domains.length} domains`);
    const extra = otherCounts.length ? ` (plus ${otherCounts.join(", ")})` : "";

    $("#results_count").text(`${totalCount.toLocaleString()} genes${extra}`);
    renderPagination(totalCount, state.limit, state.offset);
}

function renderSummary(datasetData, geneData) {
    // Datasets section
    const dsContainer = $("#summary-dataset-results");
    dsContainer.empty();

    (datasetData.results || []).forEach((item) => {
        let title = `${item.dataset_html}`;
        if (item.name) title = `${title} - ${item.name}`;
        const subtitle = item.species_common_name || "";
        const description = item.species_description;
        const badges = item.species_meta
            .map((m) => m.value)
            .filter((v) => !title.includes(v) && !subtitle.includes(v));
        const thumbnail = item.image_url || item.species_image_url || "";
        const url = getViewUrl("atlas", { dataset: item.slug });
        const query = state.q;
        appendSummaryResult("summary-dataset-results",
            query ? highlightMatch(title, query) : title,
            url,
            query ? highlightMatch(subtitle, query) : subtitle,
            query && description ? highlightMatch(description, query) : description,
            badges.map(b => query ? highlightMatch(b, query) : b),
            thumbnail);
    });
    $("#summary-dataset-count").text(`(${(datasetData.count || 0).toLocaleString()} total)`);

    // Genes section
    const geneContainer = $("#summary-gene-results");
    geneContainer.empty();

    const geneItems = geneData.genes || [];
    geneItems.forEach((item) => {
        const gene = item.gene;
        const species_name = item.species || "";
        const description = item.description || "";
        const domains = item.domains || [];
        const url = getViewUrl("gene_entry", { species: species_name, gene });
        const query = state.q;
        appendSummaryResult("summary-gene-results",
            query ? highlightMatch(gene, query) : gene,
            url,
            query ? highlightMatch(species_name, query) : species_name,
            query && description ? highlightMatch(description, query) : description,
            query ? domains.map(d => highlightMatch(d, query)) : domains,
            "");
    });

    let totalGeneCount = geneItems.length;
    const extras = [];
    if (geneData.gene_lists && geneData.gene_lists.length) extras.push(`${geneData.gene_lists.length} lists`);
    if (geneData.gene_modules && geneData.gene_modules.length) extras.push(`${geneData.gene_modules.length} modules`);
    if (geneData.domains && geneData.domains.length) extras.push(`${geneData.domains.length} domains`);
    const extraText = extras.length ? ` (${extras.join(", ")})` : "";
    $("#summary-gene-count").text(`(${totalGeneCount} genes${extraText})`);

    // Show summary, hide category view
    $("#summary-view").show();
    $("#category-view").hide();
}

function getCategoryCounts(query, species) {
    const params = { q: query, limit: 1 };
    if (species) params.species = species.replace("_", " ");

    const datasetsUrl = getViewUrl("rest:dataset-list", params);
    const geneCountParams = { q: query, limit: 1 };
    if (species) geneCountParams.species = species.replace("_", " ");
    const genesUrl = getViewUrl("rest:genesearch-list", geneCountParams);

    return Promise.all([
        fetch(datasetsUrl).then((r) => r.json()),
        fetch(genesUrl).then((r) => r.json()),
    ]);
}

function updateCategoryCounts(datasetCount, geneData) {
    const geneCount = (geneData.genes_count || 0) +
        (geneData.gene_lists_count || 0) +
        (geneData.gene_modules_count || 0) +
        (geneData.domains_count || 0);

    $("#count-datasets").text(`(${(datasetCount || 0).toLocaleString()})`);
    $("#count-genes").text(`(${(geneCount || 0).toLocaleString()})`);
}

export function loadSearchResults() {
    state = readStateFromUrl();
    const { q, category, species, limit, offset } = state;

    if (!q) return;

    showLoading();
    updateSidebar();

    const params = {
        q: q,
        limit: limit,
        offset: offset,
    };
    if (species) params.species = species.replace("_", " ");

    if (!category) {
        // Summary mode: fetch both datasets and genes
        const dsParams = { ...params, limit: Math.min(limit, 6) };
        const geneParams = { q: q, limit: 3 };
        if (species) geneParams.species = species.replace("_", " ");

        const dsUrl = getViewUrl("rest:dataset-list", dsParams);
        const gsUrl = getViewUrl("rest:genesearch-list", geneParams);
        console.log("[search] fetching datasets:", dsUrl);
        console.log("[search] fetching genes:", gsUrl);

        Promise.all([
            fetch(dsUrl).then((r) => r.json()),
            fetch(gsUrl).then((r) => r.json()),
        ])
            .then(([datasetData, geneData]) => {
                $("#loading-spinner").hide();

                if ((!datasetData.results || !datasetData.results.length) &&
                    (!geneData.genes || !geneData.genes.length)) {
                    showEmpty(q);
                    return;
                }

                renderSummary(datasetData, geneData);

                const count = (datasetData.count || 0) + (geneData.genes ? geneData.genes.length : 0);
                $("#results_count").text(`${count.toLocaleString()} results`);

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
                $("#loading-spinner").hide();
                $("#summary-view").hide();
                $("#category-view").show();

                if (!data.results || !data.results.length) {
                    showEmpty(q);
                    return;
                }

                renderDatasets(data);

                getCategoryCounts(q, species).then(([dsData, geneData]) => {
                    updateCategoryCounts(dsData.count || 0, geneData);
                }).catch(() => {});
            })
            .catch(() => {
                showError();
            });
    } else if (category === "genes") {
        const geneParams = { q: q, limit: limit };
        if (species) geneParams.species = species.replace("_", " ");
        fetch(getViewUrl("rest:genesearch-list", geneParams))
            .then((res) => res.json())
            .then((data) => {
                $("#loading-spinner").hide();
                $("#summary-view").hide();
                $("#category-view").show();

                const hasGenes = data.genes && data.genes.length;
                const hasOthers = (data.gene_lists && data.gene_lists.length) ||
                    (data.gene_modules && data.gene_modules.length) ||
                    (data.domains && data.domains.length);

                if (!hasGenes && !hasOthers) {
                    showEmpty(q);
                    return;
                }

                renderGeneGeneList(data);

                getCategoryCounts(q, species).then(([dsData, geneData]) => {
                    updateCategoryCounts(dsData.count || 0, geneData);
                }).catch(() => {});
            })
            .catch(() => {
                showError();
            });
    }
}

export function initSearchPage() {
    console.log("[search] initSearchPage called, URL:", window.location.href);
    state = readStateFromUrl();
    console.log("[search] state:", state);

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
                if (isInitial) { isInitial = false; return; }
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
