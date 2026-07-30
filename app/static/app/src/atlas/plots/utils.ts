/**
 * Shared utilities for tables and DataTables.
 */

export function buildDataQuery(data) {
    let ordering;
    if (data.order && data.order[0]) {
        const o = data.order[0];
        ordering = (o.dir == "desc" ? "-" : "") + o.name;
    }

    const params = {
        offset: data.start,
        limit: data.length,
        q: data.search.value,
        ordering: ordering,
    };
    return params;
}

export function filterData(data) {
    const json = JSON.parse(data);
    json.recordsTotal = json.count;
    json.recordsFiltered = json.count;
    json.data = json.list;
    return JSON.stringify(json);
}
