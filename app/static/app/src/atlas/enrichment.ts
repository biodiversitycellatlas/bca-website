/**
 * Gene ontology enrichment page.
 */

import $ from "jquery";
import "ion-rangeslider";
window.$ = $;

import { getViewUrl } from "../utils/urls.ts";
import { getUserLists } from "./modals/list_editor.ts";

import { createEnrichmentTable } from "./tables/enrichment_table.ts";
import { createWordCloud } from "./plots/word_cloud.ts";
import { createSemanticSimilarityPlot } from "./plots/semantic_similarity.ts";

/**
 * Simplify multiple select values into a comma-separated string
 * and update form submission.
 */
export function handleFormSubmit(id, dataset) {
    // Simplify multiple select data into a single comma-separated value
    $("form").on("submit", function (e) {
        e.preventDefault();

        // Modify form URL
        const formData = new FormData(this);
        const url = new URL(e.target.action);
        for (const [key, value] of formData.entries()) {
            url.searchParams.set(key, value);
        }

        // Get values
        const multiple = [ "gene_lists" ]
        for (const i in multiple) {
            const param = multiple[i];
            const values = formData.getAll(param);
            url.searchParams.set(param, values.join(","));

            // Process values from user lists as hidden query parameters
            if (param == "gene_lists") {
                // Get genes from user lists
                const lists = getUserLists(`${id}_${param}`, dataset);
                const matches = lists.filter((list) => values.includes(list.name));
                let genes = matches.flatMap((list) => list.items);

                // Get remaining lists
                const names = matches.flatMap((list) => list.name);
                const diff = values.filter((value) => !names.includes(value));
                genes = diff.concat(genes);

                // Set query parameter
                url.searchParams.set("genes", genes.join(","));
            }
        }

        // Maintain commas in query params
        const href = url.href.replaceAll("%2C", ",");
        window.location.href = href;
    });
}

export function prepareEnrichmentResults(species, dataset, genes) {
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
            createEnrichmentTable("enrichment", species, dataset, data);
        })
        .catch((err) => {
            console.error("Error loading enrichment data:", err);
        });
}
