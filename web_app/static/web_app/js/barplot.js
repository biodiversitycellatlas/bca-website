function createExpressionBarPlot(id, gene, gene_data) {
    var chart = {
  		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  		"title": {
    		"text": gene,
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
	  	"datasets": { "gene_data": gene_data },
	  	"transform": [
	  	    {"calculate": "toNumber(datum.metacell__name)", "as": "metacell__name"},
	  	    {"calculate": "datum.umifrac * 10", "as": "umifrac"}
	  	],
	  	"data": {"name": "gene_data"},
	  	"repeat": {"row": ["umifrac", "fold_change"]},
	  	"spec": {
	  	    "width": "container",
	  	    "mark": {"type": "bar", "tooltip": {"content": "data"}},
	  	    "encoding": {
	  	        "x": {"field": "metacell__name"},
	  	        "y": {"field": {"repeat": "row"}, "aggregate": "sum"},
	  	        "color": {
	  	            "field": "metacell__type",
	  	            "scale": {"range": {"field": "metacell__color"}}
	  	        }
            }
        }
    };
    vegaEmbed(id, chart)
   		.then(res => { metacellProjectionView = res.view; })
    	.catch(console.error);
}
