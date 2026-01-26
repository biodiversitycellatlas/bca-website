import { describe, it, expect } from "bun:test";
import { highlightMatch, addWordBreakOpportunities, slugify, escapeString } from "../ts/utils/utils";

describe("highlightMatch", () => {
  it("returns null if content is null", () => {
    expect(highlightMatch(null, "test")).toBeNull();
  });

  it("wraps matches with <span class='search-highlight'>", () => {
    const result = highlightMatch("Hello world, hello!", "hello");
    expect(result).toBe("<span class='search-highlight'>Hello</span> world, <span class='search-highlight'>hello</span>!");
  });

  it("ignores matches inside HTML tags", () => {
    const content = "<div>hello</div>";
    expect(highlightMatch(content, "div")).toBe(content);
  });
});

describe("addWordBreakOpportunities", () => {
  it("returns null if content is null", () => {
    expect(addWordBreakOpportunities(null, "test")).toBeNull();
  });

  it("adds <wbr> after matches", () => {
    const result = addWordBreakOpportunities("Hello world, hello!", "hello");
    expect(result).toBe("Hello<wbr> world, hello<wbr>!");
  });

  it("ignores matches inside HTML tags", () => {
    const content = "<span>hello</span>";
    expect(addWordBreakOpportunities(content, "span")).toBe(content);
  });
});

describe("slugify", () => {
  it("converts text to lowercase, replaces spaces and dots, removes special chars", () => {
    expect(slugify("Hello World!")).toBe("hello-world");
    expect(slugify("Multiple   spaces...here")).toBe("multiple-spaces-here");
    expect(slugify("Clean#this@up")).toBe("cleanthisup");
  });

  it("handles multiple hyphens correctly", () => {
    expect(slugify("hello---world")).toBe("hello-world");
  });
});

describe("escapeString", () => {
  it("escapes regex special characters", () => {
    expect(escapeString("file.name")).toBe("file\\.name");
    expect(escapeString("a+b*c?")).toBe("a\\+b\\*c\\?");
    expect(escapeString("[hello]")).toBe("\\[hello\\]");
  });

  it("converts input to string if needed", () => {
    expect(escapeString(123)).toBe("123");
  });
});
