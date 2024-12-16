/* Update values of all checkboxes for vega */
function updateCheckboxValue(el) { el.value = el.checked; }
$('input[type="checkbox"]').each(function() {
	this.value = this.checked;
	this.setAttribute('onclick', 'updateCheckboxValue(this);');
});

function createMetacellProjection(id, species, urls) {
    var params = new URLSearchParams({ species: species, limit: 0 });
    var sc_data_url = urls['sc_data'] + "?" + params.toString(),
        mc_data_url = urls['mc_data'] + "?" + params.toString(),
        mc_links_url = urls['mc_links'] + "?" + params.toString();
    console.log(sc_data_url, mc_data_url, mc_links_url);

    var chart = {
  		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
	  	"title": {
    		"text": {"expr": "data('sc_data').length + ' cells, ' + data('mc_data').length + ' metacells'"},
    		"fontWeight": "normal",
    		"anchor": "start"
  		},
	  	"width": "container",
	  	"height": "container",
	  	"params": [
	  		{ "name": "showCells", "bind": { "element": "#projection-cells" } },
	  		{ "name": "showMetacells", "bind": { "element": "#projection-metacells" } },
	  		{ "name": "showLabels", "bind": { "element": "#projection-labels" } },
	  		{ "name": "showLinks", "bind": { "element": "#projection-links" } }
	  	],
		"layer": [ {
			"data": { "name": "sc_data", "url": sc_data_url },
  			"mark": { "type": "circle", "tooltip": {"encoding": "data"} },
	  		"params": [
	  			{ "name": "brush", "select": {"type": "interval"} }
	  		],
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"color": {"field": "metacell_type"},
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
  			"data": { "name": "mc_links", "url": mc_links_url },
  			"mark": "rule",
	  		"encoding": {
	    		"x":  {"field": "metacell.x",  "type": "quantitative"},
	    		"x2": {"field": "metacell2.x", "type": "quantitative"},
	    		"y":  {"field": "metacell.y",  "type": "quantitative"},
	    		"y2": {"field": "metacell2.y", "type": "quantitative"},
	    		"color": {"value": "#B7B7B7"},
	    		"opacity": {
			    	"condition": { "test": "showLinks == 'false'", "value": 0 }
    			}
	    	}
  		}, {
  			"data": { "name": "mc_data", "url": mc_data_url },
  			"mark": {"type": "circle", "tooltip": {"encoding": "data"}},
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"size": {"value": 400},
	    		"color": {"field": "type", 
	    			"scale": {"range": {"field": "color"}},
	    			"legend":{"title": "Cell type annotation"}
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
  			"mark": "text",
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"text": {"field": "name"},
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
			"style": { "cell": { "stroke": "transparent" } },
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
   		.then(res => { viewMetacellProjection = res.view; })
    	.catch(console.error);
}
