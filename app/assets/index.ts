/**
 * Use bun to minimize and compile the following external assets
 */

// JS imports
import $ from "jquery";
import "bootstrap";

import * as d3 from "d3";
import * as vega from "vega";
import * as vegalite from "vega-lite";
import vegaEmbed from "vega-embed";

import "datatables.net-bs5";
import "datatables.net-select-bs5";
import "ion-rangeslider";
import "@selectize/selectize";

// CSS imports
import "bootstrap/dist/css/bootstrap.min.css";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "datatables.net-bs5/css/dataTables.bootstrap5.min.css";
import "datatables.net-select-bs5/css/select.bootstrap5.min.css";
import "ion-rangeslider/css/ion.rangeSlider.min.css";
import "@selectize/selectize/dist/css/selectize.bootstrap5.css";

// Fonts
import "@fontsource/rubik"; // Rubik typeface

window.$ = $;
