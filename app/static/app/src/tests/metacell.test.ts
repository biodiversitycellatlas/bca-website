import { describe, it, expect } from "bun:test";
import { getMetacellIndex } from "../utils/metacell";
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

describe("convertToRange", () => {
    it("convert metacell names into ranges", () => {
        expect(convertToRange("acrmil01_MC_00001,acrmil01_MC_00002,acrmil01_MC_00004")).toBe("1-2,4");
    });

    it("convert integer names into ranges", () => {
        expect(convertToRange("1,2,3,5")).toBe("1-3,5");
    });

    it("handle a single metacell", () => {
        expect(convertToRange("acrmil01_MC_00004")).toBe("4");
    });

    it("keep metacell names without a trailing number", () => {
        expect(
            convertToRange("Neuron_MC,acrmil01_MC_00002,acrmil01_MC_00001,acrmil01_MC_00004")
        ).toBe("1-2,4,Neuron_MC");
    });
});
