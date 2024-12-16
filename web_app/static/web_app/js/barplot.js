function createExpressionBarPlot(id, species, gene, url) {
	var params = new URLSearchParams({
		species: species,
		genes: gene,
		limit: 0
	});
	var apiURL = url + "?" + params.toString();

    var chart = {
  		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  		"title": {
    		"text": gene,
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
	  	"transform": [
	  	    {"calculate": "toNumber(datum.metacell_name)", "as": "metacell_name"},
	  	    {"calculate": "datum.umifrac * 10", "as": "umifrac"}
	  	],
	  	"data": {"name": "gene_data", "url": apiURL},
	  	"repeat": {"row": ["umifrac", "fold_change"]},
	  	"spec": {
	  	    "width": "container",
	  	    "mark": {"type": "bar", "tooltip": {"content": "data"}},
	  	    "encoding": {
	  	        "x": {"field": "metacell_name"},
	  	        "y": {"field": {"repeat": "row"}, "aggregate": "sum"},
	  	        "color": {
	  	            "field": "metacell_type",
	  	            "scale": {"range": {"field": "metacell_color"}}
	  	        }
            }
        }
    };
    vegaEmbed(id, chart)
   		.then(res => { viewExpression = res.view; })
    	.catch(console.error);
}
