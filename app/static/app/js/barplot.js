function createExpressionBarPlot(id, gene, data) {
    var chart = {
  		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  		//"title": { "text": gene, "fontWeight": "normal", "anchor": "start" },
	  	"transform": [
	  	    {"calculate": "toNumber(datum.metacell_name)", "as": "metacell_name"},
	  	    {"calculate": "datum.umifrac * 10", "as": "umifrac"},
	  	    {"fold": ["umifrac", "fold_change"]}
	  	],
	  	"data": {"name": "gene_data", "values": data},
  	    "width": "container",
  	    "mark": {"type": "circle", "tooltip": {"content": "data"}},
  	    "encoding": {
  	        "x": {"field": "metacell_name"},
  	        "y": {"field": "key", "title": ""},
  	        "size": {
  	            "field": "value",
  	            "type": "quantitative",
  	            "impute": {"value": 0},
  	            "legend": null
  	        },
  	        "color": {
  	            "field": "metacell_type",
  	            "scale": {"range": {"field": "metacell_color"}},
  	            "legend": null
  	            // "legend": { "orient": "bottom", "direction": "horizontal", "columns": 4 }
  	        },
  	        "tooltip": [
                {"field": "metacell_type"},
                {"field": "umi_raw"},
                {"field": "umifrac"},
                {"field": "fold_change"}
            ]
        }
    };
    vegaEmbed(id, chart)
   		.then(res => { viewExpression = res.view; })
    	.catch(console.error);
}
