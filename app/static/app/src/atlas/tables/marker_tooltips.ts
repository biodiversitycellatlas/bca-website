/**
 * Marker tooltips for cell type tree nodes.
 *
 * Hover a node's marker-count circle to show its markers, click to pin,
 * and dragging the header detaches the tooltip and moves it.
 */

import DataTable from "datatables.net-bs5";
import "datatables.net-responsive-bs5";

import {
    linkDomains,
    linkGeneLists,
    makeLinkGene,
    round,
    roundPercentage,
    roundSignificantDigits,
} from "./utils.ts";


const tooltips = new Map();

// Track tooltip drag behaviour
let drag = null;

/**
 * Marker tooltip for a single node in a tree.
 */
class MarkerTooltip {
    circle = null; // Circle size based on number of markers
    table = null; // Markers table
    pinned = false; // Pinned tooltip
    detached = false; // Detached tooltip
    hideTimer = null; // Time before hiding (allows user to reach the tooltip)

    /**
     * @param {string} name - Node name.
     * @param {Object} data - Tooltip data: { dataset, markers, color, isInternal }.
     */
    constructor(name, data) {
        this.name = name;
        const template = document.getElementById("marker-tooltip-template");
        this.el = template.content.firstElementChild.cloneNode(true);
        this.el.dataset.node = name;
        this.body = this.el.querySelector(".marker-tooltip-body");
        const title = this.el.querySelector(".marker-tooltip-title");
        title.textContent = name;
        const badge = this.el.querySelector(".marker-tooltip-count");
        const tfCount = data.markers.filter((m) => (m.genelists ?? []).includes("Transcription factors")).length;
        badge.textContent = `${data.markers.length} ${data.markers.length === 1 ? "marker" : "markers"}${tfCount ? ` (${tfCount} TFs)` : ""}`;
        // Color the grip, title, and badge with the node's color.
        if (data.color) {
            title.style.color = data.color;
            this.el.querySelector(".marker-tooltip-icon").style.color = data.color;
            badge.style.backgroundColor = data.color;
        }
        this.el.addEventListener("mouseenter", () => clearTimeout(this.hideTimer));
        this.el.addEventListener("mouseleave", () => this.scheduleHide());
        // Focusing only makes sense for internal nodes (a tip is a one-node tree)
        if (data.isInternal) {
            this.el
                .querySelector(".marker-tooltip-focus")
                .addEventListener("click", () => {
                    document.dispatchEvent(new CustomEvent("hierarchy:focus-node", { detail: this.name }));
                });
        } else {
            this.el.querySelector(".marker-tooltip-focus")?.remove();
        }
        this.toFront();
    }

    /**
     * Show the tooltip anchored to its circle.
     *
     * @param {SVGElement} circle - Circle to anchor the tooltip to.
     * @param {Object} data - Tooltip data: { dataset, markers, color, isInternal }.
     */
    show(circle, data) {
        this.circle = circle;
        clearTimeout(this.hideTimer);

        // Populate once, on the first show (data is unchanged afterwards)
        if (this.el.classList.contains("d-none")) this.populate(data);
        if (!this.detached) this.reposition();
    }

    /** Populate the tooltip's content and unhide it. */
    populate(data) {
        this.body.scrollTop = 0;
        this.toFront();
        this.el.classList.remove("d-none");
        this.table = this.createTable(data);
    }

    /** Bring the tooltip above every previously created one */
    toFront() {
        document.body.appendChild(this.el);
    }

    /** Position the tooltip next to its anchored circle, within the viewport */
    reposition() {
        if (!this.circle) return;
        const rect = this.circle.getBoundingClientRect();

        const offset = 12;
        const margin = 8;
        const { innerWidth } = window;

        // Show below the marker circle, centered on it, clamped to the viewport
        const top = rect.bottom + offset;
        const centeredLeft = rect.left + rect.width / 2 - this.el.offsetWidth / 2;
        const left = Math.max(margin, Math.min(centeredLeft, innerWidth - this.el.offsetWidth - margin));

        // Point the arrow at the circle's center (relative to the tooltip)
        this.el.style.setProperty("--marker-tooltip-arrow", `${rect.left + rect.width / 2 - left}px`);
        this.el.style.left = `${left}px`;
        this.el.style.top = `${top}px`;
    }

    /** Move the tooltip to x/y */
    dragTo(x, y) {
        const plotOptions = document.querySelector(".sticky-plot-options");
        const toolbarBottom = plotOptions?.getBoundingClientRect().bottom ?? 0;
        this.el.style.left = `${x}px`;
        this.el.style.top = `${Math.max(toolbarBottom, Math.min(y, window.innerHeight - this.el.offsetHeight - 8))}px`;
    }

    /** Remove the tooltip */
    close() {
        clearTimeout(this.hideTimer);
        this.table?.destroy();
        this.table = null;
        this.el.remove();
        tooltips.delete(this.name);
    }

    /** Pin the tooltip */
    pin() {
        this.pinned = true;
        clearTimeout(this.hideTimer);
    }

    /** Close after small delay */
    scheduleHide() {
        if (this.pinned || drag) return;
        clearTimeout(this.hideTimer);
        this.hideTimer = setTimeout(() => this.close(), 150);
    }

    /**
     * (Re)build the marker table inside the body.
     *
     * @param {Object} data - Tooltip data: { dataset, markers }.
     * @returns {DataTable|null} The new DataTable, or null if there are no markers.
     */
    createTable(data) {
        const { markers, dataset } = data;
        if (!markers.length) {
            // The shell persists, so keep the table and just show a message row.
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 10;
            cell.textContent = "No markers";
            row.appendChild(cell);
            this.body.querySelector("table tbody").replaceChildren(row);
            return null;
        }
        const linkGene = makeLinkGene(dataset);
        const table = new DataTable(this.body.querySelector("table"), {
            data: markers.map((m) => ({
                gene: m.gene,
                description: m.description,
                domains: m.domains,
                genelists: m.genelists,
                p_value: m.p_value,
                q_value: m.q_value,
                log2fc: m.avg_log2fc,
                pct1: m.pct_1,
                pct2: m.pct_2,
                specificity: Math.max(m.pct_1 - m.pct_2, 0),
            })),
            columns: [
                { data: "gene", title: "Gene", render: linkGene, className: "all" },
                { data: "description", title: "Description", className: "truncate all" },
                { data: "domains", title: "Domains", render: linkDomains, className: "truncate all" },
                { data: "genelists", title: "Gene lists", render: linkGeneLists, className: "truncate all" },
                { data: "p_value", title: "p-value", render: roundSignificantDigits, className: "max-mobile-p" },
                { data: "q_value", title: "q-value", render: roundSignificantDigits, className: "max-mobile-p" },
                { data: "log2fc", title: "log2 Fold-Change", render: round, className: "max-mobile-p" },
                { data: "pct1", title: "Gene-expressing cells (node)", render: roundPercentage, className: "max-mobile-p" },
                { data: "pct2", title: "Gene-expressing cells (sister node)", render: roundPercentage, className: "max-mobile-p" },
                { data: "specificity", title: "Specificity", render: roundPercentage, className: "all" },
            ],
            order: [[9, "desc"]],
            scrollY: "180px",
            scrollCollapse: true,
            paging: false,
            lengthChange: false,
            responsive: true,
            language: {
                info: "_TOTAL_ markers",
                infoFiltered: "(_MAX_ total)",
                infoEmpty: "No matching markers",
            },
            layout: {
                topEnd: "search",
                topStart: "info",
                bottomEnd: null,
                bottomStart: null,
            },
        });
        return table;
    }
}

/**
 * Get the marker tooltip for a node, creating it if needed.
 *
 * @param {string} name - Node name.
 * @param {Object} data - Tooltip data: { dataset, markers, color, isInternal }.
 * @returns {MarkerTooltip} The tooltip for the node.
 */
function getOrCreateTooltip(name, data) {
    let t = tooltips.get(name);
    if (!t) {
        t = new MarkerTooltip(name, data);
        tooltips.set(name, t);
    }
    return t;
}

/**
 * Attach tooltip behaviors.
 */
export function initMarkerTooltips() {
    // Keep each anchored tooltip next to its node while scrolling/resizing
    const repositionTooltips = () => {
        for (const t of tooltips.values()) {
            if (!t.detached && !t.el.classList.contains("d-none")) t.reposition();
        }
    };
    window.addEventListener("scroll", repositionTooltips, true);
    window.addEventListener("resize", repositionTooltips);

    // Drag a tooltip by its header
    document.addEventListener("mousedown", (e) => {
        const header = e.target.closest(".marker-tooltip-header");
        // Buttons in the header must not start a drag (re-appending the tooltip
        // mid-press would cancel their click event)
        if (!header || e.target.closest(".marker-tooltip-close, .marker-tooltip-focus")) return;
        const el = header.closest(".marker-tooltip");
        const t = tooltips.get(el.dataset.node);
        if (!t) return;

        e.preventDefault();
        const rect = el.getBoundingClientRect();
        drag = { t, offsetX: e.clientX - rect.left, offsetY: e.clientY - rect.top };
        t.toFront();
    });

    document.addEventListener("mousemove", (e) => {
        if (!drag) return;
        const { t, offsetX, offsetY } = drag;
        t.detached = true;
        t.pinned = true;
        t.el.classList.add("no-arrow");
        t.dragTo(e.clientX - offsetX, e.clientY - offsetY);
    });

    document.addEventListener("mouseup", () => (drag = null));

    document.addEventListener("click", (e) => {
        const onTooltip = e.target.closest?.(".marker-tooltip");
        if (onTooltip) {
            // Close tooltip if clicking in X button
            if (e.target.closest(".marker-tooltip-close")) {
                tooltips.get(onTooltip.dataset.node)?.close();
            }
        } else {
            // Close unpinned tooltips if clicking outside a tooltip
            closeTooltips(false);
        }
    });
}

/**
 * Bind hover-to-show and click-to-pin to a node's marker-count circle.
 *
 * @param {SVGElement} circle - The marker-count circle.
 * @param {string} name - Node name.
 * @param {Object} data - Tooltip data: { dataset, markers, color, isInternal }.
 */
export function attachMarkerTooltip(circle, name, data) {
    // The node-styler re-runs on refresh; bind only once per element
    if (circle._markerTooltip) return;
    circle._markerTooltip = true;
    circle.addEventListener("mouseenter", () => getOrCreateTooltip(name, data).show(circle, data));
    circle.addEventListener("mouseleave", () => tooltips.get(name)?.scheduleHide());
    circle.addEventListener("click", (e) => {
        e.stopPropagation();
        const t = getOrCreateTooltip(name, data);
        t.show(circle, data);
        t.pin();
    });
}

/**
 * Close tooltips (all by default).
 *
 * @param {boolean} includePinned - Also close pinned tooltips.
 */
export function closeTooltips(includePinned = true) {
    for (const t of [...tooltips.values()]) {
        if (includePinned || !t.pinned) t.close();
    }
}
