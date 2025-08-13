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

    const regex = new RegExp(`(${query})`, "gi");
    return content.replace(regex, "<span class='search-highlight'>$1</span>");
}

