/**
 * Tree of Life visualization
 */

import vegaEmbed from "vega-embed";

/**
 * Flatten a hierarchical tree object into an array suitable for Vega.
 *
 * @param {Object} obj - Hierarchical tree object
 * @returns {Array} Flattened array with nodes containing id, parent, name, and size
 */
export function flatten(obj) {
    let id = 0;
    return _flatten2(obj);

    function _flatten2(obj, array = [], parentID = null) {
        const node = {};
        node.id = id++;
        if (parentID !== null) node.parent = parentID;
        if (obj.length) node.size = obj.length;

        if (obj.children) {
            for (const child of obj.children) {
                _flatten2(child, array, node.id);
            }
        } else {
            node.name = obj.name;
        }

        array.push(node);
        return array;
    }
}

/**
 * Fetch and parse a Newick JSON file, then flatten it.
 *
 * @param {string} file - URL or path to the JSON file
 * @returns {Promise<Array>} Flattened array of tree nodes
 */
export async function readNewickJSON(file) {
    const res = await fetch(file);
    const obj = await res.json();
    return flatten(obj);
}

/**
 * Create an interactive radial tree of life plot.
 *
 * @param {string} id - DOM element ID where the chart will be rendered
 * @param {string} file - URL or path to the Newick JSON file
 */
export function createTreeOfLife(id, file) {
    const el = document.querySelector(id);

    function getSize() {
        const w = el.clientWidth;
        const h = Math.max(400, Math.min(w * 0.6, window.innerHeight * 0.8));
        return { width: w, height: h };
    }

    function getFontSize(w) {
        return Math.max(8, Math.min(11, Math.round(w / 90)));
    }

    fetch(file)
        .then((res) => res.json())
        .then((obj) => flatten(obj))
        .then((data) => {
            const size = getSize();
            const chart = {
                $schema: "https://vega.github.io/schema/vega/v6.json",
                description: "Tree of life.",
                width: size.width,
                height: size.height,
                padding: 5,
                autosize: "none",
                signals: [
                    { name: "originX", update: "width / 2" },
                    { name: "originY", update: "height / 2" },
                    { name: "clusterSize", update: "height / 3" },
                    { name: "fontSize", value: getFontSize(size.width) },
                    {
                        name: "extent",
                        description: "initial animation",
                        init: "0",
                        on: [
                            {
                                events: "timer{10}",
                                update: "(extent >= 360 ? 360 : extent + 20)",
                            },
                        ],
                    },
                ],

                data: [
                    {
                        name: "tree",
                        values: data,
                        transform: [
                            {
                                type: "stratify",
                                key: "id",
                                parentKey: "parent",
                            },
                            {
                                type: "tree",
                                method: "cluster",
                                size: [1, { signal: "clusterSize" }],
                                separation: false,
                                as: ["alpha", "radius", "depth", "children"],
                            },
                            {
                                type: "formula",
                                expr: "(extent * datum.alpha + 270) % 360",
                                as: "angle",
                            },
                            {
                                type: "formula",
                                expr: "PI * datum.angle / 180",
                                as: "radians",
                            },
                            {
                                type: "formula",
                                expr: "datum.name ? replace(datum.name, /_/g, ' ') : ''",
                                as: "species",
                            },
                            {
                                type: "formula",
                                expr: "inrange(datum.angle, [90, 270])",
                                as: "leftside",
                            },
                            {
                                type: "formula",
                                expr: "originX + datum.radius * cos(datum.radians)",
                                as: "x",
                            },
                            {
                                type: "formula",
                                expr: "originY + datum.radius * sin(datum.radians)",
                                as: "y",
                            },
                        ],
                    },
                    {
                        name: "links",
                        source: "tree",
                        transform: [
                            { type: "treelinks" },
                            {
                                type: "linkpath",
                                shape: "orthogonal",
                                orient: "radial",
                                sourceX: "source.radians",
                                sourceY: "source.radius",
                                targetX: "target.radians",
                                targetY: "target.radius",
                            },
                        ],
                    },
                ],

                scales: [
                    {
                        name: "color",
                        type: "linear",
                        range: { scheme: "magma" },
                        domain: { data: "tree", field: "depth" },
                        zero: true,
                    },
                ],

                marks: [
                    {
                        type: "path",
                        from: { data: "links" },
                        encode: {
                            update: {
                                x: { signal: "originX" },
                                y: { signal: "originY" },
                                path: { field: "path" },
                                stroke: { value: "#CCC" },
                            },
                        },
                    },
                    {
                        type: "symbol",
                        from: { data: "tree" },
                        encode: {
                            update: {
                                size: { value: 30 },
                                x: { field: "x" },
                                y: { field: "y" },
                                fill: {
                                    scale: "color",
                                    signal: "datum.name ? datum.depth : null",
                                },
                            },
                        },
                    },
                    {
                        type: "text",
                        from: { data: "tree" },
                        encode: {
                            enter: {
                                text: { signal: "datum.species" },
                                baseline: { value: "middle" },
                            },
                            update: {
                                tooltip: {
                                    signal: "datum.name ? {'Species': datum.species, 'Depth': datum.depth} : null",
                                },
                                fontSize: { signal: "fontSize" },
                                fontWeight: { value: "normal" },
                                fill: { scale: "color", field: "depth" },
                                x: { field: "x" },
                                y: { field: "y" },
                                dx: { signal: "(datum.leftside ? -1 : 1) * 6" },
                                angle: {
                                    signal: "datum.leftside ? datum.angle - 180 : datum.angle",
                                },
                                align: {
                                    signal: "datum.leftside ? 'right' : 'left'",
                                },
                                href: {
                                    signal: "'/entry/species/' + datum.species",
                                },
                            },
                            hover: {
                                fontWeight: { value: "bold" },
                                fontSize: { value: 12 },
                                cursor: { value: "pointer" },
                            },
                        },
                    },
                ],
            };
            vegaEmbed(id, chart, { renderer: "svg" }).then((result) => {
                const view = result.view;
                const observer = new ResizeObserver(() => {
                    const newSize = getSize();
                    view.width(newSize.width)
                        .height(newSize.height)
                        .signal("fontSize", getFontSize(newSize.width))
                        .runAsync();
                });
                observer.observe(el);
            });
        });
}
