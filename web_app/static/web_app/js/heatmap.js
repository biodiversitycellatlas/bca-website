function createExpressionHeatmap(id, expr, genes, metacells) {
	console.log(expr);
    var chart = {
		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
		"title": {
    		"text": genes + ' genes, ' + metacells + ' metacells',
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
		"datasets": { "expr_data": expr },
		"height": "container",
		"transform": [{"calculate": "toNumber(datum.metacell__name)", "as": "metacell__name"}],
		"data": {"name": "expr_data"},
		"vconcat": [{
		  	"width": "container",
		  	"mark": {"type": "rect", "tooltip": {"content": "data"}},
	      	"encoding": {
	        	"x": {"field": "metacell__name", "axis": {"labels": false, "ticks": false}},
	        	"color": {"field": "metacell__color", "legend": false}
	      	}
	    }, {
	    	"width": "container",
	    	"height": 500,
			"mark": {"type": "rect", "tooltip": {"content": "data"}},
			"encoding": {
	    		"x": {
	    			"field": "metacell__name",
	    			"axis": { "labels": false, "ticks": false }
	    		},
	    		"y": {
	    			"field": "gene__name",
	    			"axis": { "labels": false, "ticks": false },
	    			"sort": {"field": "index"}
	    		},
	    		"color": {
	    			"field": "expression",
	    			//"sort": "descending",
			      	//"scale": {"scheme": "magma"},
	    			"type": "quantitative"
	    		}
		  	}
		}, {
		  	"width": "container",
		  	"mark": {"type": "rect", "tooltip": {"content": "data"}},
	      	"encoding": {
	        	"x": {"field": "metacell__name", "axis": {"labels": false, "ticks": false}},
	        	"color": {"field": "metacell__color", "legend": false}
	      	}
	    }],
		"config": { "view": { "stroke": "transparent" } }
	};
    vegaEmbed(id, chart)
   		.then(res => { expressionHeatmapView = res.view; })
    	.catch(console.error);
}