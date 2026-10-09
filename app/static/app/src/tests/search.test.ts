import { describe, it, expect, beforeEach } from "bun:test";

import { loadSearchResults } from "../search/results_page";

const APP_URLS = {
    "rest:dataset-list": "/api/datasets/",
    "rest:genesearch-list": "/api/search/gene/",
    atlas: "/atlas/DATASET_PLACEHOLDER/",
    gene_entry: "/entry/gene/SPECIES_PLACEHOLDER/GENE_PLACEHOLDER/",
    gene_list_entry: "/entry/gene-list/GENE_LIST_PLACEHOLDER/SPECIES_PLACEHOLDER/",
    gene_module_entry: "/entry/gene-module/DATASET_PLACEHOLDER/GENE_MODULE_PLACEHOLDER/",
    domain_entry: "/entry/domain/DOMAIN_PLACEHOLDER/SPECIES_PLACEHOLDER/",
};

function stubFetch() {
    global.fetch = async (url) =>
        new Response(
            JSON.stringify(
                url.includes("datasets")
                    ? { results: [{ species_meta: [] }] }
                    : { genes: [{ gene: "ATP1", species: "Human" }] },
            ),
        );
}

const isHidden = (selector: string) =>
    document.querySelector(selector)!.style.display === "none";

describe("search page", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="mockup"></div>
            <div id="sidebar" class="display-none"></div>
            <div id="summary-view" class="display-none"></div>
        `;
        window.APP_URLS = APP_URLS;
        stubFetch();
    });

    it("replaces the mockup with results when a term is searched", async () => {
        window.happyDOM.setURL("http://localhost/search/?q=ATP");
        loadSearchResults();
        await new Promise((r) => setTimeout(r, 50));

        expect(isHidden("#mockup")).toBe(true);
        expect(isHidden("#sidebar")).toBe(false);
        expect(isHidden("#summary-view")).toBe(false);
    });

    it("shows the mockup and hides the results UI when there is no query", () => {
        window.happyDOM.setURL("http://localhost/search/");
        loadSearchResults();

        expect(isHidden("#mockup")).toBe(false);
        expect(isHidden("#sidebar")).toBe(true);
        expect(isHidden("#summary-view")).toBe(true);
    });
});
