function createExpressionHeatmap(id, expr, genes, metacells) {
	console.log(expr);
    var chart = {
		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
		"title": {
    		"text": {"expr": "data('expr_data').length + ' genes, ' + data('expr').length + ' metacells'"},
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
		"datasets": { "expr_data": expr },
		"transform": [{"calculate": "toNumber(datum.metacell)", "as": "metacell"}],
		"data": {"name": "expr_data"},
		"mark": {"type": "rect", "tooltip": true},
		"width": "container",
		"height": "container",
		"encoding": {
    		"x": { "field": "metacell", "axis": { "labels": false } },
    		"y": {"field": "gene", "axis": { "labels": false }},
    		"color": {"field": "value", "type": "quantitative"}
	  	},
		"config": { "view": { "stroke": "transparent" } }
	};
    vegaEmbed(id, chart)
   		.then(res => { expressionHeatmapView = res.view; })
    	.catch(console.error);
}