import { describe, it, expect, beforeAll } from "bun:test";
import { getDataPortalUrl, getRestUrl } from "../utils/urls";

// Mock global variables
beforeAll(() => {
    window.APP_URLS = {
        gene_module_entry:
            "/entry/gene-module/DATASET_PLACEHOLDER/MODULE_PLACEHOLDER/",
        "rest:metacellcount-list": "/api/metacellcount",
        "rest:metacellgeneexpression-list": "/api/metacellgeneexpression",
        "rest:genelist-list": "/api/genelist",
    };
});

describe("getDataPortalUrl", () => {
    it("returns the base URL", () => {
        const url = getDataPortalUrl("gene_module_entry");
        expect(url).toBe("/entry/gene-module/");
    });

    it("handles missing optional placeholders gracefully", () => {
        const url = getDataPortalUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/");
    });

    it("replaces dataset and gene module placeholders correctly", () => {
        const url = getDataPortalUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            gene_module: "blue",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/blue/");
    });

    it("handles empty string and null parameters", () => {
        const url1 = getDataPortalUrl("gene_module_entry", {
            dataset: "",
            gene_module: null,
        });
        expect(url1).toBe("/entry/gene-module/");
    });

    it("appends dataset and gene module to gene module entry", () => {
        const url = getDataPortalUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            species: "fox",
            gene_module: "blue",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/blue/");
    });

    it("appends dataset only to gene module entry", () => {
        const url = getDataPortalUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
        });
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/");

        const url2 = getDataPortalUrl("gene_module_entry", {
            dataset: "vulpes-vulpes",
            species: "fox",
            gene_module: "",
        });
        expect(url2).toBe(url);
    });

    it("throws an error for unknown views", () => {
        expect(() => getDataPortalUrl("unknown:view")).toThrow(
            'URL for view "unknown:view" not found in APP_URLS.',
        );
    });
});

describe("getRestUrl", () => {
    it("returns the base URL", () => {
        const url = getRestUrl("rest:genelist-list");
        expect(url).toBe("http://localhost/api/genelist");
    });

    it("handles views without dataset or gene placeholders", () => {
        const url = getRestUrl("rest:genelist-list", { limit: 20 });
        expect(url).toBe("http://localhost/api/genelist?limit=20");
    });

    it("appends standard query parameters correctly", () => {
        const url = getRestUrl("rest:metacellcount-list", {
            dataset: "vulpes-vulpes",
            gene: "FOXA1",
            limit: 10,
        });
        expect(url).toBe(
            "http://localhost/api/metacellcount?dataset=vulpes-vulpes&gene=FOXA1&limit=10",
        );
    });

    it("ignores null or undefined parameters", () => {
        const url = getRestUrl("rest:metacellcount-list", {
            dataset: null,
            gene: undefined,
            limit: 5,
        });
        expect(url).toBe("http://localhost/api/metacellcount?limit=5");
    });

    it("appends dataset, gene, and limit for standard REST view", () => {
        const url = getRestUrl("rest:metacellcount-list", {
            dataset: "vulpes-vulpes",
            gene: "FOXA1",
            limit: 10,
        });
        expect(url).toBe(
            "http://localhost/api/metacellcount?dataset=vulpes-vulpes&gene=FOXA1&limit=10",
        );
    });

    it("handles genes for metacellgeneexpression-list", () => {
        const url = getRestUrl("rest:metacellgeneexpression-list", {
            dataset: "vulpes-vulpes",
            genes: "BRCA2",
            limit: 5,
        });
        expect(url).toBe(
            "http://localhost/api/metacellgeneexpression?dataset=vulpes-vulpes&genes=BRCA2&limit=5",
        );
    });

    it("appends extra parameters correctly", () => {
        const url = getRestUrl("rest:metacellcount-list", {
            dataset: "mus-musculus",
            gene: "BRCA2",
            limit: 15,
            species: "mouse",
            extra: "value",
        });
        expect(url).toBe(
            "http://localhost/api/metacellcount?dataset=mus-musculus&gene=BRCA2&limit=15&species=mouse&extra=value",
        );
    });
});
