import { describe, it, expect } from "bun:test";
import {
    getMetacellIndex,
    getMetacellOrder,
    getMetacellPositions,
} from "../utils/metacell";
import { convertToRange } from "../select/metacell";

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
