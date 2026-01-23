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

// Fonts
import "@fontsource/rubik"; // Rubik typeface

// Enable tooltips and popovers
import { enableTooltipsAndPopovers, getTooltip } from "./utils/tooltips.ts";
enableTooltipsAndPopovers();
