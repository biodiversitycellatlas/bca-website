import { describe, it, expect, beforeAll } from "bun:test";
import { getDataPortalUrl } from "../utils/urls";

// Mock global variables
beforeAll(() => {
    (window as any).APP_URLS = {
        "gene_module_entry": "/entry/gene-module/DATASET_PLACEHOLDER/MODULE_PLACEHOLDER/",
        "rest:metacellcount-list": "/api/metacellcount",
        "rest:metacellgeneexpression-list": "/api/metacellgeneexpression",
        "rest:genelist-list": "/api/genelist",
    };
});

describe("getDataPortalUrl", () => {
    it("appends dataset and gene module to gene module entry", () => {
        const url = getDataPortalUrl(
            "gene_module_entry",
            "vulpes-vulpes",
            null,
            null,
            { species: "fox", gene_module: "blue" },
        );
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/blue/");
    });

    it("appends dataset only to gene module entry", () => {
        const url = getDataPortalUrl("gene_module_entry", "vulpes-vulpes");
        expect(url).toBe("/entry/gene-module/vulpes-vulpes/");

        const url2 = getDataPortalUrl(
            "gene_module_entry",
            "vulpes-vulpes",
            null,
            null,
            { species: "fox", gene_module: "" },
        );
        expect(url2).toBe(url);
    });

    it("appends dataset, gene, and limit for standard REST view", () => {
        const url = getDataPortalUrl(
            "rest:metacellcount-list",
            "vulpes-vulpes",
            "FOXA1",
            10,
        );
        expect(url).toBe(
            "http://localhost/api/metacellcount?dataset=vulpes-vulpes&gene=FOXA1&limit=10",
        );
    });

    it("handles gene as array for metacellgeneexpression-list", () => {
        const url = getDataPortalUrl(
            "rest:metacellgeneexpression-list",
            "vulpes-vulpes",
            "BRCA2",
            5,
        );
        expect(url).toBe(
            "http://localhost/api/metacellgeneexpression?dataset=vulpes-vulpes&genes=BRCA2&limit=5",
        );
    });

    it("handles views without dataset or gene placeholders", () => {
        const url = getDataPortalUrl("rest:genelist-list", null, null, 20);
        expect(url).toBe("http://localhost/api/genelist?limit=20");
    });

    it("appends extra parameters correctly", () => {
        const url = getDataPortalUrl(
            "rest:metacellcount-list",
            "mus-musculus",
            "BRCA2",
            15,
            { species: "mouse", extra: "value" },
        );
        expect(url).toBe(
            "http://localhost/api/metacellcount?dataset=mus-musculus&gene=BRCA2&limit=15&species=mouse&extra=value",
        );
    });

    it("throws error if view is not in APP_URLS", () => {
        expect(() => getDataPortalUrl("unknown:view")).toThrow(
            'URL for view "unknown:view" not found in APP_URLS.',
        );
    });
});
