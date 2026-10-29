import { describe, it, expect, beforeEach } from "bun:test";
import {
    getMetacellIndex,
    getMetacellOrder,
    getMetacellPositions,
} from "../utils/metacell";
import { convertToRange, initMetacellSelect } from "../select/metacell";

describe("getMetacellIndex", () => {
    it("extract trailing number from metacell names", () => {
        expect(getMetacellIndex("acrmil01_MC_00204")).toBe(204);
        expect(getMetacellIndex("acrmil01_MC_00001")).toBe(1);
    });

    it("extract integer metacell names", () => {
        expect(getMetacellIndex("12")).toBe(12);
        expect(getMetacellIndex("30")).toBe(30);
    });

    it("return null for names without a trailing number", () => {
        expect(getMetacellIndex("Gland")).toBeNull();
        expect(getMetacellIndex(null)).toBeNull();
    });
});

describe("getMetacellOrder", () => {
    it("use stored order when available", () => {
        expect(getMetacellOrder(2, "acrmil01_MC_00204")).toBe(2);
        expect(getMetacellOrder(0, "acrmil01_MC_00001")).toBe(0);
    });

    it("fall back to the trailing number when order is null", () => {
        expect(getMetacellOrder(null, "acrmil01_MC_00204")).toBe(204);
        expect(getMetacellOrder(null, "12")).toBe(12);
    });

    it("return null when neither order nor a trailing number is available", () => {
        expect(getMetacellOrder(null, "Gland")).toBeNull();
    });
});

describe("getMetacellPositions", () => {
    it("use stored order for each metacell", () => {
        const positions = getMetacellPositions([
            { metacell_name: "mc1", metacell_order: 3 },
            { metacell_name: "mc2", metacell_order: 1 },
            { metacell_name: "mc1", metacell_order: 3 },
        ]);
        expect(positions.get("mc1")).toBe(3);
        expect(positions.get("mc2")).toBe(1);
    });

    it("fall back to the trailing number by default", () => {
        const positions = getMetacellPositions([
            { metacell_name: "acrmil01_MC_00204" },
        ]);
        expect(positions.get("acrmil01_MC_00204")).toBe(204);
    });

    it("keep the data position when the fallback is disabled", () => {
        const positions = getMetacellPositions(
            [
                { metacell_name: "mc1" },
                { metacell_name: "mc2" },
                { metacell_name: "mc1" },
            ],
            false,
        );
        expect(positions.get("mc1")).toBe(0);
        expect(positions.get("mc2")).toBe(1);
    });
});

describe("convertToRange", () => {
    it("convert metacell names into ranges", () => {
        expect(
            convertToRange(
                "acrmil01_MC_00001,acrmil01_MC_00002,acrmil01_MC_00004",
            ),
        ).toBe("1-2,4");
    });

    it("convert integer names into ranges", () => {
        expect(convertToRange("1,2,3,5")).toBe("1-3,5");
    });

    it("handle a single metacell", () => {
        expect(convertToRange("acrmil01_MC_00004")).toBe("4");
    });

    it("keep metacell names without a trailing number", () => {
        expect(
            convertToRange(
                "Neuron_MC,acrmil01_MC_00002,acrmil01_MC_00001,acrmil01_MC_00004",
            ),
        ).toBe("1-2,4,Neuron_MC");
    });
});

describe("initMetacellSelect", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <select id="metacells" multiple>
                <option value="mc1" data-type="metacells" data-text="acrmil01_MC_00001" data-celltype="Neuron" data-color="red">acrmil01_MC_00001</option>
                <option value="mc2" data-type="metacells" data-text="acrmil01_MC_00002" data-celltype="Neuron" data-color="blue">acrmil01_MC_00002</option>
                <option value="mc3" data-type="cell_types" data-text="Neuron" data-celltype="Neuron" data-color="green">Neuron</option>
            </select>
        `;
    });

    it("return a TomSelect instance", () => {
        const select = initMetacellSelect("", "");
        expect(select).toBeDefined();
        expect(select.settings.multiple).toBe(true);
        select.destroy();
    });

    it("set initial values from selected", () => {
        const select = initMetacellSelect("mc1,mc2", "");
        expect(select.getValue()).toEqual(["mc1", "mc2"]);
        select.destroy();
    });

    it("fall back to selected2 when selected is empty", () => {
        const select = initMetacellSelect("", "mc2");
        expect(select.getValue()).toEqual(["mc2"]);
        select.destroy();
    });

    it("prefer selected over selected2", () => {
        const select = initMetacellSelect("mc1", "mc2");
        expect(select.getValue()).toEqual(["mc1"]);
        select.destroy();
    });

    it("have no selection when both are empty", () => {
        const select = initMetacellSelect("", "");
        expect(select.getValue()).toEqual([]);
        select.destroy();
    });

    it("render metacell items as badge with range", () => {
        const select = initMetacellSelect("mc1", "");
        const item = select.getItem("mc1");
        expect(item).toBeDefined();
        expect(item.innerHTML).toContain("badge");
        expect(item.innerHTML).toContain("rounded-pill");
        expect(item.innerHTML).toContain("text-bg-secondary");
        select.destroy();
    });

    it("render cell type items with color circle", () => {
        const select = initMetacellSelect("mc3", "");
        const item = select.getItem("mc3");
        expect(item).toBeDefined();
        expect(item.innerHTML).toContain("fa-circle");
        select.destroy();
    });

    it("render options with color circle and text", () => {
        const select = initMetacellSelect("", "");
        const escape = (s) => s;
        const html = select.settings.render.option(
            { text: "Neuron", color: "green", metacells: true },
            escape,
        );
        expect(html).toContain("option");
        expect(html).toContain("fa-circle");
        expect(html).toContain("color: green");
        expect(html).toContain("Neuron");
        select.destroy();
    });

    it("render non-metacell options with celltype label", () => {
        const select = initMetacellSelect("", "");
        const escape = (s) => s;
        const html = select.settings.render.option(
            {
                text: "Neuron",
                color: "blue",
                metacells: false,
                celltype: "Neuron",
            },
            escape,
        );
        expect(html).toContain("option");
        expect(html).toContain("fa-circle");
        expect(html).toContain("color: blue");
        expect(html).toContain("Neuron");
        expect(html).toContain("float-end");
        select.destroy();
    });

    it("boost cell_type score over metacell score", () => {
        const select = initMetacellSelect("", "");
        const scoreFn = select.settings.score.call(select, "Neuron");
        const cellTypeScore = scoreFn({ type: "cell_types", text: "Neuron" });
        const metacellScore = scoreFn({ type: "metacells", text: "Neuron" });
        expect(cellTypeScore).toBeGreaterThan(metacellScore);
        select.destroy();
    });

    it("return zero score for non-matching queries", () => {
        const select = initMetacellSelect("", "");
        const scoreFn = select.settings.score.call(select, "ZZZZZ");
        const score = scoreFn({ type: "metacells", text: "Neuron" });
        expect(score).toBe(0);
        select.destroy();
    });
});
