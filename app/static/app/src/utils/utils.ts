/**
 * Utility functions.
 */

/**
 * Highlights all occurrences of a query within a given text.
 * Wraps matches in a <span> with class 'search-highlight' using DOM nodes,
 * so content is never reinterpreted as HTML.
 *
 * @param {string|null} content - Text to search within.
 * @param {string} query - Substring to highlight.
 * @returns {DocumentFragment|null} Fragment with highlighted matches (or null if null content).
 */
export function highlightMatch(content, query) {
    if (content === null) return null;

    const fragment = document.createDocumentFragment();
    if (!query) {
        fragment.appendChild(document.createTextNode(content));
        return fragment;
    }

    const safeQuery = escapeString(query);
    const regex = new RegExp(`(${safeQuery})`, "gi");

    let lastIndex = 0;
    let match = regex.exec(content);

    while (match !== null) {
        const matchIndex = match.index;
        const matchText = match[0];

        if (matchIndex > lastIndex) {
            fragment.appendChild(
                document.createTextNode(content.slice(lastIndex, matchIndex)),
            );
        }

        const span = document.createElement("span");
        span.className = "search-highlight";
        span.textContent = matchText;
        fragment.appendChild(span);

        lastIndex = matchIndex + matchText.length;
        match = regex.exec(content);
    }

    if (lastIndex < content.length) {
        fragment.appendChild(document.createTextNode(content.slice(lastIndex)));
    }

    return fragment;
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
