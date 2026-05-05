/**
 * Gene ontology enrichment page.
 */

import $ from "jquery";
import "ion-rangeslider";
window.$ = $;

import { getViewUrl } from "../utils/urls.ts";
import { createEnrichmentTable } from "./tables/enrichment_table.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";

/**
 * Simplify multiple select values into a comma-separated string
 * and update form submission.
 */
export function handleFormSubmit() {
    // Simplify multiple select data into a single comma-separated value
    $("form").on("submit", function (e) {
        e.preventDefault();

        // Get values
        const formData = new FormData(this);
        const values = formData.getAll("gene").join(",");

        // Modify form URL
        const url = new URL(e.target.action);
        for (const [key, value] of formData.entries()) {
            if (key === "gene") continue; // do not add gene back to URL
            url.searchParams.set(key, value);
        }
        url.searchParams.set("genes", values);

        // Maintain commas in query params
        const href = url.href.replaceAll("%2C", ",");
        window.location.href = href;
    });
}

/**
 * Fetch marker data for selected metacells and create the markers table.
 *
 * @param {string} dataset - Dataset slug.
 * @param {string} metacells - Comma-separated list of selected metacells.
 * @param {string} fc_min_type - Type of minimum fold-change filtering.
 * @param {number} fc_min - Minimum fold-change value.
 * @param {string} fc_max_bg_type - Type of maximum background fold-change filtering.
 * @param {number} fc_max_bg - Maximum background fold-change value.
 */
export function initEnrichmentTable(
    dataset,
    genes,
) {
    const url = getViewUrl("rest:enrichment-list");
    genes = genes.split(",");
    createEnrichmentTable("enrichment", dataset, url, { "dataset": dataset, "genes": genes });
}
