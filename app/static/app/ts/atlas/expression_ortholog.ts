/**
 * Load and visualize ortholog gene expression.
 */

import { getDataPortalUrl } from "../utils/urls.ts";
import { appendDataMenu } from "../buttons/data_dropdown.ts";
import { createExpressionBubblePlot } from "./plots/expression_plot.ts";
import { hideSpinner } from "./plots/plot_container.ts";

/**
 * Render expression plots for each corresponding ortholog.
 *
 * @param {string} baseGene - Reference gene used to exclude itself from orthologs.
 * @param {HTMLTemplateElement} header - Template for ortholog species header.
 * @param {HTMLTemplateElement} template - Template for ortholog dataset and plot.
 * @param {HTMLElement} container - Container element to append ortholog plots.
 * @param {Object} item - Ortholog data object, including gene name, species, datasets, and expression.
 */
function processOrtholog(baseGene, header, template, container, item) {
    const gene = item.gene_name;
    if (gene != baseGene) {
        const headerClone = document.importNode(header.content, true);

        if (item.datasets && item.datasets[0]) {
            headerClone.getElementById("ortholog-species-img").src =
                item.datasets[0].species_image_url;
            headerClone.getElementById("ortholog-species-img").alt =
                "Image of " + item.species;
        }
        headerClone.getElementById("ortholog-species").innerText = item.species;
        container.appendChild(headerClone);

        for (const d in item.datasets) {
            const dataset = item.datasets[d];

            // Header info
            const clone = document.importNode(template.content, true);
            clone.getElementById("ortholog-dataset").innerHTML =
                dataset.name || `<i>${item.species}</i>`;
            clone.getElementById("ortholog-dataset-href").href =
                `/atlas/${dataset.slug}`;

            // Dataset info
            clone.getElementById("ortholog-gene-href").innerText = gene;
            clone.getElementById("ortholog-gene-href").href =
                `/atlas/${dataset.slug}/gene/${gene}`;
            clone.getElementById("single-ortholog-plot").id =
                dataset.slug + "-" + item.gene_slug;
            container.appendChild(clone);

            // Dataset gene expression plot
            createExpressionBubblePlot(
                "#" + dataset.slug + "-" + item.gene_slug,
                gene,
                item.expression[dataset.slug],
            );
        }
    }
}

/**
 * Render expression plots for orthologs of a given gene.
 *
 * @param {string} gene - Reference gene.
 */
export function loadOrthologExpression(gene) {
    const apiURL = getDataPortalUrl("rest:ortholog-list", null, gene, 0, {
        expression: true,
    });
    appendDataMenu("orthologs", apiURL, "Ortholog expression");

    // Fetch data from the API and create plots
    const header = document.getElementById("ortholog-header-template");
    const template = document.getElementById("ortholog-template");
    const container = document.getElementById("orthologs-plot");

    fetch(apiURL)
        .then((response) => response.json())
        .then((data) => {
            if (data.length === 0) {
                container.innerHTML =
                    "<p class='text-muted'><i class='fa fa-circle-exclamation'></i> No orthologs found.</p>";
            } else {
                data.forEach((item) =>
                    processOrtholog(gene, header, template, container, item),
                );
            }
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
        })
        .finally(() => {
            hideSpinner("orthologs");
        });
}
