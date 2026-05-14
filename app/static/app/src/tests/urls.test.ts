import { describe, it, expect, beforeAll } from "bun:test";
import { getViewUrl } from "../utils/urls";

// Mock global variables
beforeAll(() => {
    window.APP_URLS = {
        gene_module_entry:
            "/entry/gene-module/DATASET_PLACEHOLDER/GENE_MODULE_PLACEHOLDER/",
        "rest:metacellcount-list": "/api/metacellcount",
        "rest:metacellgeneexpression-list": "/api/metacellgeneexpression",
        "rest:genelist-list": "/api/genelist",
    };
});

describe("getViewUrl", () => {
    it("return the base URL", () => {
        const url = getViewUrl("gene_module_entry");
        expect(url).toBe("/entry/gene-module/");
    });

    it("handle non-placeholders as query parameters", () => {
        const url = getViewUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            extra: "hello",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/?extra=hello");
    });

    it("replace dataset and gene module placeholders", () => {
        const url = getViewUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            gene_module: "blue",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/blue/");
    });

    it("handle empty string and null parameters", () => {
        const url1 = getViewUrl("gene_module_entry", {
            dataset: "",
            gene_module: null,
        });
        expect(url1).toBe("/entry/gene-module/");
    });

    it("append dataset and gene module to gene module entry", () => {
        const url = getViewUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            gene_module: "blue",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/blue/");
    });

    it("append dataset only to gene module entry", () => {
        const url = getViewUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/");

        const url2 = getViewUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            gene_module: "",
        });
        expect(url2).toBe(url);
    });

    it("throw error for unknown views", () => {
        expect(() => getViewUrl("unknown:view")).toThrow(
            'URL for view "unknown:view" not found in APP_URLS.',
        );
    });

    it("returns the base URL", () => {
        const url = getViewUrl("rest:genelist-list");
        expect(url).toBe("/api/genelist");
    });

    it("handles views without dataset or gene placeholders", () => {
        const url = getViewUrl("rest:genelist-list", { limit: 20 });
        expect(url).toBe("/api/genelist?limit=20");
    });

    it("appends standard query parameters correctly", () => {
        const url = getViewUrl("rest:metacellcount-list", {
            dataset: "vulpes-vulpes",
            gene: "FOXA1",
            limit: 10,
        });
        expect(url).toBe(
            "/api/metacellcount?dataset=vulpes-vulpes&gene=FOXA1&limit=10",
        );
    });

    it("ignores null or undefined parameters", () => {
        const url = getViewUrl("rest:metacellcount-list", {
            dataset: null,
            gene: undefined,
            limit: 5,
        });
        expect(url).toBe("/api/metacellcount?limit=5");
    });

    it("appends dataset, gene, and limit for standard REST view", () => {
        const url = getViewUrl("rest:metacellcount-list", {
            dataset: "vulpes-vulpes",
            gene: "FOXA1",
            limit: 10,
        });
        expect(url).toBe(
            "/api/metacellcount?dataset=vulpes-vulpes&gene=FOXA1&limit=10",
        );
    });

    it("handles genes for metacellgeneexpression-list", () => {
        const url = getViewUrl("rest:metacellgeneexpression-list", {
            dataset: "vulpes-vulpes",
            genes: "BRCA2",
            limit: 5,
        });
        expect(url).toBe(
            "/api/metacellgeneexpression?dataset=vulpes-vulpes&genes=BRCA2&limit=5",
        );
    });

    it("appends extra parameters correctly", () => {
        const url = getViewUrl("rest:metacellcount-list", {
            dataset: "mus-musculus",
            gene: "BRCA2",
            limit: 15,
            species: "mouse",
            extra: "value",
        });
        expect(url).toBe(
            "/api/metacellcount?dataset=mus-musculus&gene=BRCA2&limit=15&species=mouse&extra=value",
        );
    });
});
