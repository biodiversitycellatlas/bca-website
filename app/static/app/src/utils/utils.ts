/**
 * Utility functions.
 */

/**
 * Highlights all occurrences of a query within a given text.
 * Wraps matches in a <span> with class 'search-highlight'.
 *
 * @param {string|null} content - Text to search within.
 * @param {string} query - Substring to highlight.
 * @returns {string|null} Content with highlighted matches (or null if null content).
 */
export function highlightMatch(content, query) {
    if (content === null) return content;

    const regex = new RegExp(`(?<!<)(${query})(?![^<>]*>)`, "gi");
    return content.replace(regex, "<span class='search-highlight'>$1</span>");
}

/**
 * Inserts word break opportunities (`<wbr>`) after occurrences of a query string
 * within the provided content, ignoring matches inside HTML tags.
 *
 * @param {string|null} content - The text content in which to insert `<wbr>` tags.
 * @param {string} query - The substring to match and add word break opportunities after.
 * @returns {string|null} - The modified content with `<wbr>` inserted, or the original content if null.
 */
export function addWordBreakOpportunities(content, query) {
    if (content === null) return content;

    const regex = new RegExp(`(?<!<)(${query})(?![^<>]*>)`, "gi");
    return content.replace(regex, "$1<wbr>");
}

/**
 * Converts string into URL-friendly slug.
 *
 * @param {string} text - Text to slugify.
 * @returns {string} Slugified text.
 *
 * @example
 * slugify("Hello World!") // returns "hello-world"
 */
export function slugify(text) {
    return text
        .toString()
        .toLowerCase()
        .trim()
        .replace(/[\s.]+/g, "-") // Replace spaces and dots with -
        .replace(/[^\w-]+/g, "") // Remove all non-word chars
        .replace(/--+/g, "-"); // Replace multiple - with single -
}

/**
 * Escapes special characters in a string.
 *
 * @param {string} text - Text to escape.
 * @returns {string} Escaped string.
 *
 * @example
 * escapeRegex("file.name") // returns "file\\.name"
 */
export function escapeString(text) {
    return text.toString().replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); // Double backslash
}
