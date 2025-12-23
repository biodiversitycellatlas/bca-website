/**
 * Gene modules: list unique and overlapping genes.
 */

import { getDataPortalUrl } from "../utils/urls.js";
import { updateDataMenu } from "../buttons/data_dropdown.js";
import { hideSpinner } from "../plots/plot_container.js";

function createModuleHeader(
    id,
    modules,
    count,
    collapseId = null,
    collapseN = 10,
) {
    const template = document.getElementById(`${id}-module-header-template`);
    const clone = template.content.cloneNode(true);

    let name = modules.length > 1 ? "Intersecting" : modules[0];
    clone.querySelector(".module-name").textContent = name;

    let label = modules.length > 1 ? "intersecting" : "unique";
    label = `${count} ${label} gene` + (count == 1 ? "" : "s");
    clone.querySelector(".gene-count").textContent = label;

    if (collapseId) {
        const showBtn = clone.querySelector(".show-genes-btn");
        showBtn.setAttribute("href", `#${collapseId}`);
        showBtn.setAttribute("aria-controls", collapseId);

        // Disable button to expand genes if all genes are shown
        if (collapseN >= count) showBtn.classList.add("disabled");
    }

    // Disable all buttons if list has no genes
    if (count == 0) {
        const buttons = clone.querySelectorAll("[class$='-btn']");
        buttons.forEach((btn) => btn.classList.add("disabled"));
    }
    return clone;
}

function createGeneList(id, dataset, genes, collapseId = null, collapseN = 10) {
    const template = document.getElementById(`${id}-module-genes-template`);
    const clone = template.content.cloneNode(true);
    const ul = clone.querySelector(".gene-list");

    genes.forEach((gene, index) => {
        const li = document.createElement("li");
        li.classList.add("text-truncate");

        // Append gene URL
        const gene_url = getDataPortalUrl("atlas_gene", dataset, gene);
        const a = document.createElement("a");
        a.href = gene_url;
        a.textContent = gene;
        li.appendChild(a);

        // Collapse list after the Nth item
        if (collapseId && index >= collapseN) {
            li.classList.add("collapse");
            li.id = collapseId;
        }
        ul.appendChild(li);
    });
    return clone;
}

function populateModuleGeneList(
    id,
    dataset,
    modules,
    genes,
    headerEl,
    geneListEl,
    collapseId,
    collapseN = 10,
) {
    let header = createModuleHeader(
        id,
        modules,
        genes.length,
        collapseId,
        collapseN,
    );
    let geneList = createGeneList(id, dataset, genes, collapseId, collapseN);

    headerEl.appendChild(header);
    geneListEl.appendChild(geneList);
}

function createModuleGeneLists(id, dataset, data) {
    const module = data.module,
        module_genes = data.unique_genes_module_list,
        module2 = data.module2,
        module2_genes = data.unique_genes_module2_list,
        intersecting_genes = data.intersecting_genes_list;

    const headerEl = document.getElementById(`${id}-module-header`);
    const geneListEl = document.getElementById(`${id}-module-genes`);

    // Clear existing content
    headerEl.innerHTML = "";
    geneListEl.innerHTML = "";

    // Populate gene lists
    populateModuleGeneList(
        id,
        dataset,
        [module],
        module_genes,
        headerEl,
        geneListEl,
        "collapseModule",
    );
    populateModuleGeneList(
        id,
        dataset,
        [module, module2],
        intersecting_genes,
        headerEl,
        geneListEl,
        "collapseIntersecting",
    );
    populateModuleGeneList(
        id,
        dataset,
        [module2],
        module2_genes,
        headerEl,
        geneListEl,
        "collapseModule2",
    );

    // Style header element to be sticky for long genes list
    headerEl.classList.add("sticky-top");
    headerEl.style.top = "100px";
    headerEl.style.backgroundColor = "var(--subnavbar-bg-color)";
    headerEl.style.backdropFilter = "var(--subnavbar-blur)";
    headerEl.style.zIndex = "1000";

    // Append horizontal line to header element
    const hr = document.createElement("hr");
    hr.classList.add("my-2");
    headerEl.appendChild(hr);
}

/**
 * Load overlapping and unique genes
 *
 * @param {string} id - Container ID for the heatmap plot.
 * @param {string} dataset - Dataset slug to fetch expression data for.
 * @param {Array} modules - Name of gene modules to compare.
 */
export function loadModuleGeneLists(id, dataset, modules = null) {
    if (!modules) return;

    let url = getDataPortalUrl(
        "rest:genemodulesimilarity-list",
        dataset,
        null,
        0,
        { list_genes: 1, modules: modules.join(",") },
    );

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            createModuleGeneLists(id, dataset, data[0]);
        })
        .catch((error) => console.error("Error fetching data:", error))
        .finally(() => hideSpinner(id));

    updateDataMenu(id, url, "Gene lists");
}
