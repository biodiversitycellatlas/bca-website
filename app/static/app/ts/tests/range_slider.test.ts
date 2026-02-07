import { describe, test, expect, beforeEach } from "bun:test";
import $ from "jquery";
import { initRangeSlider } from "../utils/range_slider";

describe("Range Slider Utils", () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <input type="text" id="slider" />
            <input type="text" id="slider2" />
            <span id="label">5 eggs</span>
        `;
    });

    test("initRangeSlider initializes slider", () => {
        // Check initial label
        const label = $("#label");
        expect(label.text()).toBe("5 eggs");

        // Initalize slider
        const opts = { min: 0, max: 5, from: 3, step: 0.1 };
        const slider = initRangeSlider("#slider", opts, [
            "#label",
            undefined,
            " eggs",
        ]);

        // Check if slider was started as expected
        expect(slider).toBeDefined();
        expect(slider.options.min).toBe(0);
        expect(slider.options.max).toBe(5);
        expect(slider.options.from).toBe(3);
        expect(slider.options.step).toBe(0.1);
        expect(slider.options.from_min).toBe(null);

        // Update label
        expect(label).toBeDefined();
        expect(label.text()).toBe("3 eggs");

        // Update slider's from_min based on slider2's from value
        const slider2 = initRangeSlider("#slider2", opts, [
            "#label",
            "#slider",
            " eggs",
        ]);
        expect(slider.options.from_min).toBe(slider2.options.from);
    });
});
