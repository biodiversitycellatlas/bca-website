import { beforeAll, beforeEach, describe, expect, it } from "bun:test";

import {
    initSearchPage,
    loadSearchResults,
    updateQuery,
} from "../search/results_page";
import { initSpeciesSelect } from "../select/species";

// Mock global variables
beforeAll(() => {
    window.APP_URLS = {
        "rest:dataset-list": "/api/datasets/",
        "rest:genesearch-list": "/api/search/gene/",
        atlas: "/atlas/DATASET_PLACEHOLDER/",
        gene_entry: "/entry/gene/SPECIES_PLACEHOLDER/GENE_PLACEHOLDER/",
        gene_list_entry:
            "/entry/gene-list/GENE_LIST_PLACEHOLDER/SPECIES_PLACEHOLDER/",
        gene_module_entry:
            "/entry/gene-module/DATASET_PLACEHOLDER/GENE_MODULE_PLACEHOLDER/",
        domain_entry: "/entry/domain/DOMAIN_PLACEHOLDER/SPECIES_PLACEHOLDER/",
    };
});

const SEARCH_RESULTS = {
    dataset: {
        slug: "homo-sapiens",
        dataset_html: "<b>Human</b> (adult)",
        name: "Adult",
        species_common_name: "Human",
        species_description:
            "A bilateral organism commonly found in major cities around the world.",
        species_meta: [{ value: "adult" }, { value: "healthy" }],
    },
    gene: {
        gene: "ATP1",
        species: "Human",
        species_image_url: "/human.png",
        description: "ATP gene",
        domains: ["ATP domain"],
    },
    gene_list: { name: "ATP_list", description: "List", gene_count: 1200 },
    gene_module: {
        module: "ATP_module",
        dataset: "human-atlas",
        dataset_label: "Human atlas",
        gene_count: 0,
        image_url: "/module.png",
    },
    domain: {
        name: "ATP_domain",
        description: "Domain",
        gene_count: 2,
    },
} as const;

const categories = [
    "datasets",
    "genes",
    "gene_lists",
    "gene_modules",
    "domains",
];

/** Build the minimal search-page DOM used by these tests. */
function buildPage() {
    const buttonTemplate = (category) => `
        <button class="category-btn" data-category="${category}">
            <span class="category-count"></span>
        </button>`;

    const limitTemplate = (limit) =>
        `<a class="limit-btn" data-limit="${limit}" href="#">${limit}</a>`;

    const sectionTemplate = (category) => `
        <section data-category="${category}">
            <a class="summary-count" data-category="${category}"></a>
            <div class="summary-results"></div>
        </section>`;

    const categoryButtons = ["", ...categories].map(buttonTemplate).join("");
    const limitButtons = [12, 24, 36, 48, 60].map(limitTemplate).join("");
    const sections = categories.map(sectionTemplate).join("");

    document.body.innerHTML = `
        <div id="mockup"></div>
        <div id="loading-spinner"></div>
        <div id="sidebar">${categoryButtons}${limitButtons}</div>
        <span id="results_count"></span>
        <div id="summary-view">${sections}</div>
        <div id="category-view"><div id="results"></div></div>
        <div id="no-results-state"><span id="empty-query"></span></div>
        <div id="error-state"></div>
        <nav id="pagination-nav"><ul id="pagination"></ul></nav>
        <button id="clear-species"></button>
        <select id="species-select-"></select>
        <form id="search-form"><input name="q"></form>
        <template id="result-template">
            <div class="result">
                <a class="result-title"></a>
                <a class="result-subtitle"></a>
                <img class="result-image d-none">
                <div class="result-description"></div>
                <div class="result-badges"></div>
            </div>
        </template>`;
}

/** Create a JSON response from data */
function response(data) {
    return new Response(JSON.stringify(data));
}

/** Set the browser URL to a search page */
function setSearchUrl(search = "") {
    const url = new URL(`/search/${search}`, window.location.origin);
    window.happyDOM.setURL(url.href);
}

/** Return whether the selected element is hidden */
function isHidden(selector: string) {
    return document.querySelector(selector)!.style.display === "none";
}

/** Resolve when the search spinner is hidden */
function waitForSearch() {
    const spinner = document.querySelector("#loading-spinner")!;
    if (spinner.style.display === "none") return Promise.resolve();

    return new Promise<void>((resolve, reject) => {
        const observer = new MutationObserver(() => {
            if (spinner.style.display !== "none") return;
            observer.disconnect();
            clearTimeout(timeout);
            resolve();
        });
        const timeout = setTimeout(() => {
            observer.disconnect();
            reject(new Error("Search did not finish before the timeout"));
        }, 1000);

        observer.observe(spinner, {
            attributes: true,
            attributeFilter: ["style"],
        });
    });
}

/** Mock fetch */
function stubFetch(handler?: (url: string) => Response) {
    const requested: string[] = [];
    global.fetch = async (input) => {
        const url = String(input);
        requested.push(url);
        if (handler) return handler(url);

        const genes = [{ gene: "ATP1", species: "Human" }];
        const result = url.includes("datasets")
            ? { results: [], count: 0 }
            : { genes, genes_count: 1 };
        return response(result);
    };
    return requested;
}

describe("search page", () => {
    beforeEach(() => {
        buildPage();
        setSearchUrl();
        stubFetch();
    });

    it("shows the mockup and hides the results UI when there is no query", () => {
        document.querySelector(".category-count")!.textContent = "(12)";
        loadSearchResults();

        expect(isHidden("#mockup")).toBe(false);
        expect(isHidden("#sidebar")).toBe(true);
        expect(isHidden("#summary-view")).toBe(true);
        expect(document.querySelector(".category-count")!.textContent).toBe("");
    });

    it("fetches and renders summary results with normalized species and category counts", async () => {
        setSearchUrl("?q=ATP&species=mus-musculus&limit=12");

        const requested = stubFetch((url) =>
            url.includes("datasets")
                ? response({ results: [SEARCH_RESULTS.dataset], count: 1 })
                : response({
                      genes: [SEARCH_RESULTS.gene],
                      genes_count: 2,
                      gene_lists: [],
                      gene_lists_count: 3,
                      gene_modules: [],
                      gene_modules_count: 4,
                      domains: [],
                      domains_count: 5,
                  }),
        );

        await loadSearchResults();

        expect(requested).toHaveLength(2);
        expect(requested[0]).toContain("species=Mus+musculus");
        expect(requested[1]).toContain("species=Mus+musculus");
        expect(requested[0]).toContain("limit=6");
        expect(requested[1]).toContain("limit=3");
        expect(isHidden("#summary-view")).toBe(false);
        expect(isHidden("#sidebar")).toBe(false);

        const result = document.querySelectorAll(".summary-results .result");
        expect(result).toHaveLength(2);

        const categoryCount = document.querySelector(
            '.category-btn[data-category="gene_modules"] .category-count',
        );
        expect(categoryCount?.textContent).toBe("(4)");

        const resultsCount =
            document.querySelector("#results_count")?.textContent;
        expect(resultsCount).toMatch(/15 results in \d+\.\d{2}s/);
    });

    it("show empty state for no results", async () => {
        setSearchUrl("?q=missing");
        stubFetch((url) => {
            const empty = url.includes("datasets")
                ? { results: [] }
                : { genes: [] };
            return response(empty);
        });
        await loadSearchResults();

        expect(isHidden("#no-results-state")).toBe(false);
        const emptyElem = document.querySelector("#empty-query");
        expect(emptyElem?.textContent).toBe("missing");

        setSearchUrl("?q=missing&category=genes");
        await loadSearchResults();
        expect(isHidden("#no-results-state")).toBe(false);
    });

    it("show error state if request fails", async () => {
        setSearchUrl("?q=ATP");
        global.fetch = async () => {
            throw new Error("network error");
        };
        await loadSearchResults();
        expect(isHidden("#error-state")).toBe(false);
        const resultsCount =
            document.querySelector("#results_count")?.textContent;
        expect(resultsCount).toBe("Error loading results");

        setSearchUrl("?q=ATP&category=genes");
        await loadSearchResults();
        expect(isHidden("#error-state")).toBe(false);
    });

    it("renders category result variants and paginates dataset results", async () => {
        const resultData = {
            datasets: { results: [SEARCH_RESULTS.dataset], count: 25 },
            genes: { genes: [SEARCH_RESULTS.gene], genes_count: 1 },
            gene_lists: {
                gene_lists: [SEARCH_RESULTS.gene_list],
                gene_lists_count: 1,
            },
            gene_modules: {
                gene_modules: [SEARCH_RESULTS.gene_module],
                gene_modules_count: 1,
            },
            domains: { domains: [SEARCH_RESULTS.domain], domains_count: 1 },
        };
        let activeCategory: keyof typeof resultData = "datasets";
        const requested = stubFetch(() => response(resultData[activeCategory]));

        setSearchUrl("?q=ATP&category=datasets&limit=12");
        await initSearchPage();

        expect(requested[0]).toContain("/api/datasets/");
        expect(document.querySelectorAll("#results .result")).toHaveLength(1);
        expect(document.querySelector("#results_count")?.textContent).toMatch(
            /25 results in/,
        );
        expect(isHidden("#pagination-nav")).toBe(false);
        expect(
            document.querySelectorAll("#pagination .page-link"),
        ).toHaveLength(5);

        document
            .querySelector('#pagination a[aria-label="Next"]')!
            .dispatchEvent(
                new Event("click", { bubbles: true, cancelable: true }),
            );
        await waitForSearch();
        const params = new URLSearchParams(window.location.search);
        expect(params.get("offset")).toBe("12");
        expect(requested.at(-1)).toContain("offset=12");

        for (const category of [
            "genes",
            "gene_lists",
            "gene_modules",
            "domains",
        ]) {
            activeCategory = category as keyof typeof resultData;
            setSearchUrl(`?q=ATP&category=${category}`);
            await loadSearchResults();
            const results = document.querySelectorAll("#results .result");
            expect(results).toHaveLength(1);
        }

        const resultBadges = document.querySelector(
            "#results .result-badges",
        )?.textContent;
        expect(resultBadges).toContain("2 genes");
    });

    it("hides pagination for one page and handles invalid category and query updates", async () => {
        setSearchUrl("?q=ATP&category=genes&limit=12");
        stubFetch(() =>
            response({ genes: [SEARCH_RESULTS.gene], genes_count: 1 }),
        );
        await loadSearchResults();
        expect(isHidden("#pagination-nav")).toBe(true);

        setSearchUrl("?q=ATP&category=unknown");
        await loadSearchResults();
        expect(isHidden("#loading-spinner")).toBe(false);

        setSearchUrl("?q=ATP&category=genes&offset=24");
        await updateQuery("category", "datasets");
        let params = new URLSearchParams(window.location.search);
        expect(params.get("offset")).toBe(null);

        await updateQuery("species", "");
        params = new URLSearchParams(window.location.search);
        expect(params.has("species")).toBe(false);

        await updateQuery("offset", "-1");
        params = new URLSearchParams(window.location.search);
        expect(params.get("offset")).toBe("-1");
    });

    it("wires page controls, search submission, species changes, and browser navigation", async () => {
        await initSearchPage();

        document
            .querySelector('.category-btn[data-category="genes"]')!
            .dispatchEvent(new Event("click", { bubbles: true }));
        await waitForSearch();
        let params = new URLSearchParams(window.location.search);
        expect(params.get("category")).toBe("genes");

        document
            .querySelector('.limit-btn[data-limit="36"]')!
            .dispatchEvent(
                new Event("click", { bubbles: true, cancelable: true }),
            );
        await waitForSearch();
        params = new URLSearchParams(window.location.search);
        expect(params.get("limit")).toBe("36");

        const species = document.querySelector(
            "#species-select-",
        ) as HTMLSelectElement;
        species.innerHTML =
            '<option value="mus-musculus" selected>Mouse</option>';
        species.value = "mus-musculus";
        species.dispatchEvent(new Event("change", { bubbles: true }));
        await waitForSearch();
        params = new URLSearchParams(window.location.search);
        expect(params.get("species")).toBe("mus-musculus");

        document
            .querySelector("#clear-species")!
            .dispatchEvent(new Event("click", { bubbles: true }));
        await waitForSearch();
        params = new URLSearchParams(window.location.search);
        expect(params.has("species")).toBe(false);
        expect(species.value).toBe("");

        const form = document.querySelector("#search-form") as HTMLFormElement;
        (form.elements.namedItem("q") as HTMLInputElement).value = "new query";
        form.dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true }),
        );
        await waitForSearch();
        params = new URLSearchParams(window.location.search);
        expect(params.get("q")).toBe("new query");

        document
            .querySelector('.summary-count[data-category="domains"]')!
            .dispatchEvent(
                new Event("click", { bubbles: true, cancelable: true }),
            );
        await waitForSearch();
        params = new URLSearchParams(window.location.search);
        expect(params.get("category")).toBe("domains");

        setSearchUrl("?q=back&category=genes");
        window.dispatchEvent(new PopStateEvent("popstate"));
        await waitForSearch();
        expect(
            document.querySelector("#results .result-title")?.textContent,
        ).toBe("ATP1");
    });

    it("does not run a search when opening the species selector", async () => {
        setSearchUrl("?q=ATP&species=mus-musculus");
        const species = document.querySelector(
            "#species-select-",
        ) as HTMLSelectElement;
        species.innerHTML = `
            <option value=""></option>
            <option value="mus-musculus" selected>Mouse</option>
            <option value="homo-sapiens">Human</option>
        `;
        species.value = "mus-musculus";
        const requested = stubFetch();

        await initSearchPage();
        const select = initSpeciesSelect(
            "",
            "mus-musculus",
            "none",
            false,
            "",
            "",
        );
        select.open();

        const params = new URLSearchParams(window.location.search);
        expect(params.get("species")).toBe("mus-musculus");
        expect(requested).toHaveLength(2);
    });

    it("clears the Tom Select species control", async () => {
        setSearchUrl("?q=ATP&species=mus-musculus");
        const species = document.querySelector(
            "#species-select-",
        ) as HTMLSelectElement;
        species.innerHTML =
            '<option value=""></option><option value="mus-musculus" selected>Mouse</option>';
        await initSearchPage();
        const select = initSpeciesSelect(
            "",
            "mus-musculus",
            "none",
            false,
            "",
            "",
        );

        document
            .querySelector("#clear-species")!
            .dispatchEvent(new Event("click", { bubbles: true }));
        await waitForSearch();

        expect(select.getValue()).toBe("");

        const params = new URLSearchParams(window.location.search);
        expect(params.has("species")).toBe(false);
    });

    it("clears the species query when the selector is unavailable", async () => {
        setSearchUrl("?q=ATP&species=mus-musculus");
        document.querySelector("#species-select-")!.remove();
        await initSearchPage();

        document
            .querySelector("#clear-species")!
            .dispatchEvent(new Event("click", { bubbles: true }));
        await waitForSearch();

        const params = new URLSearchParams(window.location.search);
        expect(params.has("species")).toBe(false);
    });
});
