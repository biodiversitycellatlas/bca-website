/**
 * Dropdown to view, download and copy links to data.
 */

/* global $ */

/**
 * Get the current URL from a data view button.
 *
 * @param {string} id - Data menu identifier.
 * @param {number} index - Index of the view button.
 * @returns {URL} URL object for the data view.
 */
function getDataURL(id, index) {
    let url = $(`a[name="data_view_${id}"]`)[index].href;
    url = new URL(url, window.location.href);
    return url;
}

/**
 * Download data from the specified view button URL.
 *
 * @param {string} id - Data menu identifier.
 * @param {number} index - Index of the download button.
 */
function downloadData(id, index) {
    // Disable download button and change icon to spinner
    const button = $(`a[name="data_download_${id}"]`)[index];
    button.classList.add("disabled");
    const previousInnerHTML = button.innerHTML;
    button.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Downloading...';

    // Prepare filename
    let url = getDataURL(id, index);
    let format = url.searchParams.get("format");
    let filename = url.pathname.split("/").filter(Boolean).pop();

    // Fetch and download data
    fetch(url)
        .then((response) => response.blob())
        .then((blob) => {
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `${filename}.${format}`;
            link.click();
        })
        .catch((error) => console.error("Error downloading file:", error))
        .finally(() => {
            button.classList.remove("disabled");
            button.innerHTML = previousInnerHTML;
        });
}

/**
 * Copy the API URL for a data view button to the clipboard.
 *
 * @param {string} id - Data menu identifier.
 * @param {number} index - Index of the link button.
 */
function copyDataLink(id, index) {
    const btn = $(`a[name="data_link_${id}"]`).eq(index);
    btn.addClass("disabled");

    const url = getDataURL(id, index);
    navigator.clipboard.writeText(url.href);
    btn.tooltip("show");

    setTimeout(function () {
        btn.tooltip("hide");
        btn.removeClass("disabled");
    }, 500);
}

/**
 * Update all data links to use the specified format.
 *
 * @param {string} format - Data format (such as 'csv', 'tsv', 'json').
 */
function updateDataFormat(format) {
    // Change all view buttons to the same format
    const view_btns = $(`a[name*="data_view"]`);
    for (let i = 0; i < view_btns.length; i++) {
        let url = new URL(view_btns[i].href);
        url.searchParams.set("format", format);
        view_btns[i].href = url;
    }
    localStorage.setItem("data_format", format);
}

/**
 * Apply saved data format selection or default to 'csv'.
 *
 * @param {string} id - Identifier for the data menu.
 */
function setSavedFormat(id) {
    // Get valid formats
    let valid = $(`input[name="data_format_${id}"]`)
        .map((_, el) => el.value)
        .get();

    // Set format based on saved setting (fallback to 'csv')
    let format = localStorage.getItem("data_format");
    format = valid.includes(format) ? format : "csv";

    $(`input[name="data_format_${id}"][value="${format}"]`).prop(
        "checked",
        true,
    );
    updateDataFormat(format);
}

/**
 * Initialize data format radio buttons and update links on change.
 *
 * @param {string} id - Identifier for the data menu.
 */
export function initDataFormatSelector(id) {
    setSavedFormat(id);

    // Change data format based on user selection
    $(`input[name=data_format_${id}]`).on("change", function () {
        let format = $(this).val();
        // Update all format selection elements in the page to the same value
        $(`input[type="radio"][value="${format}"]`).prop("checked", true);
        updateDataFormat(format);
    });
}

/**
 * Update the href of a dropdown menu link.
 *
 * @param {string} id - Identifier for the data menu.
 * @param {HTMLElement} elem - Dropdown list item element.
 * @param {string} url - New URL to assign.
 * @returns {HTMLElement} The updated element.
 */
function updateDataMenuLink(id, elem, url) {
    // View data
    elem.querySelector(`a[name="data_view_${id}"]`).href = url;
    return elem;
}

/**
 * Populate dropdown menu.
 *
 * @param {string} id - The prefix identifier of the HTML elements.
 * @param {string|Object} urls - String of single URL dictionary where keys
 *    are labels (overridden by `labels` if provided) and values are URLs.
 * @param {string[]} [labels] - Optional string or array of labels used to
 *    identify each link.
 *
 * @example
 * appendDataMenu('heatmap', {
 *     sc_data: '/api/v1/singlecells/?species=Mus+musculus',
 *     mc_data: '/api/v1/metacells/?species=Mus+musculus'
 * }, ['Single-cell data', 'Metacell data']);
 *
 * @example
 * appendDataMenu('metacells', '/api/v1/metacells/?species=Mus+musculus',
 *                'Metacell data');
 */
export function appendDataMenu(id, urls, labels) {
    let template = document.getElementById(`data_template_${id}`),
        dropdownMenu = document.getElementById(`data_dropdown_${id}`),
        dropdownFooter = document.getElementById(`data_footer_${id}`);

    if (typeof urls == "string") {
        urls = { [labels]: urls };
        labels = undefined;
    }

    // Find last index of data download option for this identifier
    let lastIndex = $(
        `ul[id="data_dropdown_${id}"] > li[name="data_download_option"]`,
    )
        .last()
        .data("index");

    let i = lastIndex !== undefined ? lastIndex + 1 : 0;
    for (let key in urls) {
        const clone = document.importNode(template.content, true);
        let label = labels === undefined ? key : labels[i];
        clone.querySelector("label").textContent = label;
        clone.querySelector("li").setAttribute("data-index", i);

        // View data
        let url = urls[key];
        updateDataMenuLink(id, clone, url);

        // Download data
        clone.querySelector(`a[name="data_download_${id}"]`).onclick =
            (function (id, i) {
                return function () {
                    downloadData(id, i);
                };
            })(id, i);

        // Copy API link
        clone.querySelector(`a[name="data_link_${id}"]`).onclick = (function (
            id,
            i,
        ) {
            return function () {
                copyDataLink(id, i);
            };
        })(id, i);

        dropdownMenu.insertBefore(clone, dropdownFooter);
        i++;
    }
}

/**
 * Update an existing data dropdown menu item or append it if not present.
 *
 * @param {string} id - Data menu identifier.
 * @param {string} url - URL to assign to the menu item.
 * @param {string} label - Label identifying the menu item to update.
 */
export function updateDataMenu(id, url, label) {
    let li = $(
        `ul[id="data_dropdown_${id}"] > li[name="data_download_option"] > label:contains("${label}")`,
    )
        .last()
        .parent()[0];
    if (li === undefined) {
        // If running for the first time, append data instead
        appendDataMenu(id, url, label);
    } else {
        // Update URL
        updateDataMenuLink(id, li, url);
    }
}
