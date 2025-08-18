import { getDataPortalUrl } from "../utils/urls.js";
import { createGeneTable } from "./tables/gene_table.js";
import { appendDataMenu } from "../buttons/data_dropdown.js";

export function loadGeneCorrelationTable(id, dataset, gene) {
    // Get lists from API
    var corrURL = getDataPortalUrl("rest:correlated-list", dataset, gene);
    appendDataMenu(id, corrURL, "Correlation table (current page)");
    createGeneTable(`${id}_table`, dataset, corrURL, true, "single");
}
