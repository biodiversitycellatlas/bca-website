/**
 * Use bun to minimize and compile external assets.
 */

// CSS imports
import "bootstrap/dist/css/bootstrap.min.css";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "datatables.net-bs5/css/dataTables.bootstrap5.min.css";
import "datatables.net-select-bs5/css/select.bootstrap5.min.css";
import "ion-rangeslider/css/ion.rangeSlider.min.css";
import "@selectize/selectize/dist/css/selectize.bootstrap5.css";
import "tom-select/dist/css/tom-select.bootstrap5.min.css";

// Fonts
import "@fontsource/rubik"; // Rubik typeface

// Enable tooltips and popovers
import { enableTooltipsAndPopovers } from "./utils/tooltips.ts";
enableTooltipsAndPopovers();
