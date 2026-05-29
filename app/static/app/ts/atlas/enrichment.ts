/**
 * Gene ontology enrichment page.
 */

import $ from "jquery";
import "ion-rangeslider";
window.$ = $;

import { getViewUrl } from "../utils/urls.ts";
import { createEnrichmentTable } from "./tables/enrichment_table.ts";
import { createWordCloud } from "./plots/word_cloud.ts";
import { createSemanticSimilarityPlot } from "./plots/semantic_similarity.ts";

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

export function prepareEnrichmentResults(dataset, genes) {
    const url = getViewUrl("rest:enrichment-list");
    const payload = { dataset: dataset, genes: genes.split(",") };

    fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    })
        .then((res) => {
            if (!res.ok) throw new Error("Request failed");
            return res.json();
        })
        .then((data) => {
            createSemanticSimilarityPlot("#semantic-plot", data);
            createWordCloud("#words-plot", data);
            createEnrichmentTable("enrichment", dataset, data);
        })
        .catch((err) => {
            console.error("Error loading enrichment data:", err);
        });
}
