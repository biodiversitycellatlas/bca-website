function createExpressionHeatmap(id, species, data) {
    var chart = {
		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
		"height": "container",
		"data": {"name": "exprData", "values": data },
		"transform": [
			{"calculate": "toNumber(datum.metacell_name)", "as": "metacell_name"},
			{"joinaggregate": [
		        {"op": "distinct", "field": "gene_name", "as": "gene_count"},
		        {"op": "distinct", "field": "metacell_name", "as": "metacell_count"}
		    ]}
		],
		"params": [{
      		"name": "title",
      		"expr": "data('data_0')[0].gene_count + ' genes, ' + data('data_0')[0].metacell_count + ' metacells'"
		}],
		"title": {
    		"text": {"expr": "title"},
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
		"vconcat": [{
		  	"width": "container",
		  	"mark": "rect",
	      	"encoding": {
	        	"x": {"field": "metacell_name", "axis": {"labels": false, "ticks": false}},
	        	"color": {
	        		"field": "metacell_color", "legend": false,
	    			"scale": {"range": {"field": "metacell_color"}}
	    		},
	        	"tooltip": [ {"field": "metacell_name"}, {"field": "metacell_type"}, {"field": "metacell_color"} ]
	      	}
	    }, {
	    	"width": "container",
	    	"height": 500,
			"mark": {"type": "rect", "tooltip": {"content": "data"}},
			"encoding": {
	    		"x": {
	    			"field": "metacell_name",
	    			"axis": { "labels": false, "ticks": false }
	    		},
	    		"y": {
	    			"field": "gene_name",
	    			"axis": { "labels": false, "ticks": false },
	    			"sort": {"field": "index"}
	    		},
	    		"color": {
	    			"field": "log2_fold_change",
	    			//"sort": "descending",
			      	//"scale": {"scheme": "magma"},
	    			"type": "quantitative",
	    			"title": "Log\u2082 FC"
	    		}
		  	}
		}, {
		  	"width": "container",
		  	"mark": "rect",
	      	"encoding": {
	        	"x": {"field": "metacell_name", "axis": {"labels": false, "ticks": false}},
	        	"color": {
	        		"field": "metacell_color", "legend": false,
	    			"scale": {"range": {"field": "metacell_color"}}
	    		},
	        	"tooltip": [ {"field": "metacell_name"}, {"field": "metacell_type"} ]
	      	}
	    }],
		"config": { "view": { "stroke": "transparent" } }
	};
    vegaEmbed(id, chart)
   		.then(res => { viewExpressionHeatmap = res.view; })
    	.catch(console.error);
}
