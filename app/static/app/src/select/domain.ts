import TomSelect from "tom-select";
import { getViewUrl } from "../utils/urls.ts";

function renderOption(item, escape) {
    const count = item.gene_count
        ? ` <span class="text-muted small">${escape(item.gene_count)} genes</span>`
        : "";
    return `<div class='option'>${escape(item.name)}${count}</div>`;
}

function renderItem(item, escape) {
    return `<div class='option'>${escape(item.name)}</div>`;
}

export function initDomainSelect(domain) {
    const select = new TomSelect("#domain-select", {
        valueField: "name",
        searchField: ["name"],
        preload: "focus",
        onChange: function (value) {
            if (value === domain) return;
            const url = new URL(window.location.href);
            if (value) {
                url.searchParams.set("domain", value);
            } else {
                url.searchParams.delete("domain");
            }
            url.searchParams.delete("page");
            window.location.href = url;
        },
        onBlur: function () {
            if (!this.getValue()) {
                this.setValue(domain);
            }
        },
        render: { item: renderItem, option: renderOption },
        load: function (query, callback) {
            const params = { order_by_gene_count: true, limit: 20 };
            if (query.length) params.q = query;
            fetch(getViewUrl("rest:domain-list", params))
                .then((res) => res.json())
                .then((data) => callback(data.results))
                .catch(() => callback());
        },
    });

    if (domain) {
        fetch(getViewUrl("rest:domain-list", { q: domain, order_by_gene_count: true, limit: 1 }))
            .then((res) => res.json())
            .then((data) => {
                if (data.results.length > 0) {
                    select.addOption(data.results[0]);
                    select.setValue(domain);
                }
            });
    }

    return select;
}
