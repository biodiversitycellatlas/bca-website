/**
* Renders a Sankey diagram to compare SAMap scores between metacell types from two species
*
* Based on https://github.com/PBI-David/Deneb-Showcase
*
* @param {string} id - CSS selector of the target HTML element
* @param {Array<Object>} data - Array of objects containing:
*   - dataset: slug of the first dataset
*   - metacell_type: cell type from the first dataset
*   - metacell_color: color for metacell_type
*   - dataset2: slug of the second dataset
*   - metacell_type2: cell type from the second dataset
*   - metacell_color2: color for metacell_type2
*   - samap: SAMap score between the two metacell types
*/
function createSAMapSankey(id, data) {
	var chart = {
		"$schema": "https://vega.github.io/schema/vega/v6.json",
		"width": 250,
		"height": 400,
		"signals": [
			{
				"name": "gap",
				"value": 3,
				"description": "Gap between rectangles"
			},
			{
				"name": "textPadding",
				"value": 8,
				"description": "Text padding"
			},
			{
				"name": "innerPadding",
				"value": 0.9,
				"description": "Inner padding"
			}
		],
		"data": [
			{ "name": "input", "values": data },
			{
				"name": "stacks",
				"source": "input",
				"transform": [
					{"type": "formula", "as": "end", "expr": "['metacell_type', 'metacell_type2']"},
					{"type": "formula", "as": "name", "expr": "[ datum.metacell_type, datum.metacell_type2]"},
					{"type": "flatten", "fields": ["end", "name"]},
					{
						"type": "aggregate",
						"fields": ["samap"],
						"groupby": ["end", "name"],
						"ops": ["sum"],
						"as": ["samap"]
					},
					{"type": "formula", "as": "stack", "expr": "datum.end === 'metacell_type' ? 1 : 2"}
				]
			},
			{
				"name": "maxSamap",
				"source": ["stacks"],
				"transform": [
					{
						"type": "aggregate",
						"fields": ["samap"],
						"groupby": ["stack"],
						"ops": ["sum"],
						"as": ["samap"]
					}
				]
			},
			{
				"name": "plottedStacks",
				"source": ["stacks"],
				"transform": [
					{
						"type": "formula",
						"as": "spacer",
						"expr": "(data('maxSamap')[0].samap/100) * gap"
					},
					{"type": "formula", "as": "type", "expr": "['data', 'spacer']"},
					{
						"type": "formula",
						"as": "spacedSamap",
						"expr": "[datum.samap, datum.spacer]"
					},
					{"type": "flatten", "fields": ["type", "spacedSamap"]},
					{
						"type": "stack",
						"groupby": ["stack"],
						"field": "spacedSamap",
						"offset": "center"
					},
					{"type": "formula", "expr": "datum.samap/2 + datum.y0 - 1", "as": "yc"}
				]
			},
			{
				"name": "finalTable",
				"source": "plottedStacks",
				"transform": [{"type": "filter", "expr": "datum.type == 'data'"}]
			},
			{
				"name": "linkTable",
				"source": "input",
				"transform": [
					{
						"type": "lookup",
						"from": "finalTable",
						"key": "name",
						"values": ["y0", "stack"],
						"fields": ["metacell_type", "metacell_type2"],
						"as": ["metacell_typeStacky0", "metacell_typeStack", "metacell_type2Stacky0", "metacell_type2Stack"]
					},
					{
						"type": "stack",
						"groupby": ["metacell_type"],
						"field": "samap",
						"as": ["syi0", "syi1"]
					},
					{
						"type": "formula",
						"expr": "((datum.samap)/2) + datum.syi0 + datum.metacell_typeStacky0",
						"as": "syc"
					},
					{
						"type": "stack",
						"groupby": ["metacell_type2"],
						"field": "samap",
						"as": ["dyi0", "dyi1"]
					},
					{
						"type": "formula",
						"expr": "((datum.samap)/2) + datum.dyi0 + datum.metacell_type2Stacky0",
						"as": "dyc"
					},
					{
						"type": "linkpath",
						"orient": "horizontal",
						"shape": "diagonal",
						"sourceY": {"expr": "scale('y', datum.syc)"},
						"sourceX": {"expr": "scale('x', 1) + bandwidth('x')"},
						"targetY": {"expr": "scale('y', datum.dyc)"},
						"targetX": {"expr": "scale('x', 2)"}
					},
					{"type": "formula", "expr": "range('y')[0] - scale('y', datum.samap)", "as": "strokeWidth"}
				]
			}
		],
		"scales": [
			{
				"name": "x",
				"type": "band",
				"range": "width",
				"domain": [1, 2],
				"paddingInner": {"signal": "innerPadding"}
			},
			{
				"name": "y",
				"range": "height",
				"domain": {"data": "finalTable", "field": "y1"}
			},
			{
				"name": "color",
				"type": "ordinal",
				"range": {"scheme": "rainbow"},
				"domain": {"data": "stacks", "field": "name"}
			}
		],
		"marks": [
			{
				"type": "rect",
				"from": {"data": "finalTable"},
				"encode": {
					"update": {
						"x": {"scale": "x", "field": "stack"},
						"width": {"scale": "x", "band": 1},
						"y": {"scale": "y", "field": "y0"},
						"y2": {"scale": "y", "field": "y1"},
						"fill": {"scale": "color", "field": "name"},
						"fillOpacity": {"value": 0.75},
						"stroke": {"scale": "color", "field": "name"}
					},
					"hover": {
						"tooltip": {
							"signal": "{'Cell type': datum.name, 'SAMap': format(datum.samap, '.2f')}"
						},
						"fillOpacity": {"value": 1}
					}
				}
			},
			{
				"type": "path",
				"from": {"data": "linkTable"},
				"clip": true,
				"encode": {
					"update": {
						"strokeWidth": {"field": "strokeWidth"},
						"path": {"field": "path"},
						"strokeOpacity": {"signal": "0.3"},
						"stroke": {"field": "metacell_type2", "scale": "color"}
					},
					"hover": {
						"strokeOpacity": {"value": 1},
						"tooltip": {
							"signal": "{'Cell type 1': datum.metacell_type, 'Cell type 2': datum.metacell_type2, 'SAMap': format(datum.samap, '.2f')}"
						}
					}
				}
			},
			{
				"type": "group",
				"zindex": 1,
				"clip": false,
				"marks": [
					{
						"type": "text",
						"from": {"data": "finalTable"},
						"encode": {
							"update": {
								"x": {
									"scale": "x", "field": "stack", "offset": {
										"signal": "datum.stack == 1 ? -textPadding : bandwidth('x') + textPadding"
									}
								},
								"text": {"field": "name"},
								"align": {"signal": "datum.stack == 1 ? 'right' : 'left'"},
								"yc": {"scale": "y", "signal": "datum.yc"}
							}
						}
					}
				]
			}
		]
	};
    vegaEmbed(id, chart)
   		.then(res => { viewSAMapSankey = res.view; })
    	.catch(console.error);
}
