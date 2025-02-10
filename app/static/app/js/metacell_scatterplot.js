/* Update values of all checkboxes for vega */
function updateCheckboxValue(el) { el.value = el.checked; }
$('input[type="checkbox"]').each(function() {
	this.value = this.checked;
	this.setAttribute('onclick', 'updateCheckboxValue(this);');
});

function createMetacellProjection(id, species, data, color_by_metacell_type=true, gene=null) {
    var chart = {
  		"$schema": "https://vega.github.io/schema/vega-lite/v5.json",
	  	"title": {
    		"text": {"expr": "data('sc_data').length + ' cells, ' + data('mc_data').length + ' metacells'"},
    		"subtitle": gene !== null ? gene + " expression" : null,
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
			"data": { "name": "sc_data", "values": data['sc_data'] },
  			"mark": { "type": "circle", "tooltip": {"encoding": "data"} },

  			// Avoid this transform for cells: this changes axis limits
  			// "transform": [ { "filter": "showCells == 'true'" } ],

	  		"params": [ { "name": "brush", "select": {"type": "interval"} } ],
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"color": {
	    			"condition": {
	    				"test": "datum.umifrac == null",
				        "value": "#F1F7FE"
				    },
	    			"title": "UMI/10K",
	    			"field": "umifrac",
	    			"type": "quantitative",
	    			"scale": {"scheme": "magma", "reverse": true},
	    		},
	    		"opacity": {
			    	"condition": {
        				"test": "showCells == 'true'",
        				"value": 0.7,
        				"type": "nominal"
      				},
      				"value": 0
    			},
    			"tooltip": {
    				"condition": {"test": "showCells == 'false'", "value": null}
    			}
	    	}
  		}, {
  			"data": { "name": "mc_links", "values": data['mc_links'] },
  			"mark": "rule",
  			"transform": [ { "filter": "showLinks == 'true'" } ],
	  		"encoding": {
	    		"x":  {"field": "metacell.x",  "type": "quantitative"},
	    		"x2": {"field": "metacell2.x", "type": "quantitative"},
	    		"y":  {"field": "metacell.y",  "type": "quantitative"},
	    		"y2": {"field": "metacell2.y", "type": "quantitative"},
	    		"color": {"value": "#B7B7B7"}
	    	}
  		}, {
  			"data": { "name": "mc_data", "values": data['mc_data'] },
  			"mark": {
  				"type": "circle",
  				"stroke": "white",
  				"strokeWidth": 1,
  				"tooltip": {"encoding": "data"}
  			},
  			"transform": [
			    { "calculate": "log(datum.fold_change) / log(2)", "as": "log2_fold_change" },
			    { "filter": "showMetacells == 'true'" }
			],
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"size": {"value": 400},
	    		"fill": {
	    			"title": "Log\u2082 FC",
	    			"field": "log2_fold_change",
	    			"type": "quantitative",
	    			"scale": {"scheme": "magma",  "reverse": true}
	    		},
	    		"opacity": { "value": 0.7 }
	    	}
  		}, {
  			"data": {"name": "mc_data"},
  			"mark": "text",
  			"transform": [ { "filter": "showLabels == 'true'" } ],
	  		"encoding": {
	    		"x": {"field": "x", "type": "quantitative"},
	    		"y": {"field": "y", "type": "quantitative"},
	    		"text": {"field": "name"},
	    		"opacity": { "value": 0.7 }
	    	}
  		}],
  		"config": {
  			"mark": { "invalid": null },
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

	// Colour by metacell_type
	if (color_by_metacell_type) {
		// The vega-lite conditions do not support updating the legend when
		// changing the field/type used for colouring
		chart.layer[0].encoding.color = {
			"field": "metacell_type",
			"scale": {"range": {"field": "metacell_color"}},
			"title": "Cell type"
		};
		delete chart.layer[0].transform;

		delete chart.layer[2].encoding.fill;
		chart.layer[2].encoding.color = {
			"field": "type",
			"scale": {"range": {"field": "color"}},
			"title": "Cell type"
		};
	}

    vegaEmbed(id, chart)
   		.then(res => { viewMetacellProjection = res.view; })
    	.catch(console.error);
}
