/* Update values of all checkboxes for vega */
function updateCheckboxValue(el) { el.value = el.checked; }
$('input[type="checkbox"]').each(function() {
	this.value = this.checked;
	this.setAttribute('onclick', 'updateCheckboxValue(this);');
});

function createMetacellProjection(id, sc_data, mc_data, mc_links) {
    var chart = {
  		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
	  	"description": "Scatterplot.",
	  	"title": {
    		"text": {"expr": "data('sc_data').length + ' cells, ' + data('mc_data').length + ' metacells'"},
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
	  	"width": 500,
	  	"height": 500,
	  	"params": [
	  		{ "name": "showCells", "bind": { "element": "#projection-cells" } },
	  		{ "name": "showMetacells", "bind": { "element": "#projection-metacells" } },
	  		{ "name": "showLabels", "bind": { "element": "#projection-labels" } },
	  		{ "name": "showLinks", "bind": { "element": "#projection-links" } }
	  	],
	  	"datasets": {
	  		"sc_data": sc_data,
	  		"mc_data": mc_data,
	  		"mc_links": mc_links
	  	},
		"layer": [ {
			"data": {"name": "sc_data"},
  			"mark": {"type": "circle", "tooltip": {"encoding": "data"}},
	  		"params": [
	  			{ "name": "brush", "select": {"type": "interval"} }
	  		],
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"color": {"field": "metacell_type", 
	    			"scale": {"range": {"field": "color"}}
	    		},
	    		"opacity": {
			    	"condition": {
        				"test": "showCells == 'true'",
        				"value": "0.7",
        				"type": "nominal"
      				},
      				"value": "0"
    			},
    			"tooltip": {
    				"condition": {"test": "showCells == 'false'", "value": null}
    			}
	    	}
  		}, {
  			"data": {"name": "mc_links"},
  			"mark": "rule",
	  		"encoding": {
	    		"x":  {"field": "x",  "type": "quantitative"},
	    		"x2": {"field": "x2", "type": "quantitative"},
	    		"y":  {"field": "y",  "type": "quantitative"},
	    		"y2": {"field": "y2", "type": "quantitative"},
	    		"color": {"value": "#B7B7B7"},
	    		"opacity": {
			    	"condition": { "test": "showLinks == 'false'", "value": 0 }
    			}
	    	}
  		}, {
  			"data": {"name": "mc_data"},
  			"mark": {"type": "circle", "tooltip": {"encoding": "data"}},
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"size": {"value": 400},
	    		"color": {"field": "cell_type", 
	    			"scale": {"range": {"field": "color"}}
	    		},
	    		"opacity": {
			    	"condition": {
        				"test": "showMetacells == 'true'",
        				"value": 0.7,
        				"type": "nominal"
      				},
      				"value": 0
    			},
    			"tooltip": {
    				"condition": { test: "showMetacells == 'false'", "value": null }
    			}
	    	}
  		}, {
  			"data": {"name": "mc_data"},
  			"mark": {"type": "text"},
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"text": {"field": "id"},
	    		"opacity": {
			    	"condition": {
        				"test": "showLabels == 'true'",
        				"value": 0.7,
        				"type": "nominal"
      				},
      				"value": 0
    			}
	    	}
  		}],
  		"config": {
			"style": {
		    	"cell": {
		      		"stroke": "transparent"
		    	}
		  	},
		  	"axis": {
		  		"domain": false,
		  		"grid": false,
		  		"ticks": false,
		  		"labels": false,
		  		"title": null
		  	}
		}
	};
    vegaEmbed(id, chart)
   		.then(res => { view = res.view; })
    	.catch(console.error);
}