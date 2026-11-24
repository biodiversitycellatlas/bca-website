import { describe, it, expect, beforeAll, beforeEach } from "bun:test";
import { getViewUrl, setUrlParam } from "../utils/urls";

// Mock global variables
beforeAll(() => {
    window.APP_URLS = {
        gene_module_entry:
            "/entry/gene-module/DATASET_PLACEHOLDER/GENE_MODULE_PLACEHOLDER/",
        gene_entry: "/entry/gene/SPECIES_PLACEHOLDER/GENE_PLACEHOLDER/",
        "rest:metacellcount-list": "/api/metacellcount",
        "rest:metacellgeneexpression-list": "/api/metacellgeneexpression",
        "rest:genelist-list": "/api/genelist",
        "rest:celltypetree-list": "/api/v1/cell_type_trees/",
        atlas_hierarchy: "/atlas/DATASET_PLACEHOLDER/hierarchy/",
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

    it("builds gene detail URLs with species and gene in the path", () => {
        const url = getViewUrl("gene_entry", {
            species: "Mus musculus",
            gene: "Trp53",
        });
        expect(url).toBe("/entry/gene/Mus%20musculus/Trp53/");
    });

    it("collapses the empty gene placeholder for species-only gene URLs", () => {
        const url = getViewUrl("gene_entry", { species: "mus-musculus" });
        expect(url).toBe("/entry/gene/mus-musculus/");
    });
});

describe("setUrlParam", () => {
    // The hierarchy page keeps its view options in the URL via setUrlParam
    let base;

    beforeEach(() => {
        base = new URL(
            getViewUrl("atlas_hierarchy", { dataset: "adult-mouse" }),
            window.location.origin,
        ).href;
        window.history.replaceState({}, "", base);
    });

    it("appends a non-default tree layout to the URL", () => {
        setUrlParam("tree_type", "radial", "linear");
        expect(window.location.search).toBe("?tree_type=radial");
    });

    it("updates the focused node", () => {
        window.history.replaceState({}, "", base + "?focus_node=Tips");
        setUrlParam("focus_node", "Neurons", "");
        expect(window.location.search).toBe("?focus_node=Neurons");
    });

    it("removes the param when the value is the default", () => {
        window.history.replaceState({}, "", base + "?tree_type=radial");
        setUrlParam("tree_type", "linear", "linear");
        expect(window.location.search).toBe("");
    });

    it("clears the focused node when reset", () => {
        window.history.replaceState({}, "", base + "?focus_node=Neurons");
        setUrlParam("focus_node", "", "");
        expect(window.location.search).toBe("");
    });

    it("sets an empty value without removing the param when no default is given", () => {
        setUrlParam("specificity_min", "");
        expect(window.location.search).toBe("?specificity_min=");
    });

    it("leaves other view options untouched", () => {
        window.history.replaceState({}, "", base + "?colors=true&specificity_min=20");
        setUrlParam("internal_names", "true", "false");
        expect(window.location.search).toBe(
            "?colors=true&specificity_min=20&internal_names=true",
        );
    });
});
