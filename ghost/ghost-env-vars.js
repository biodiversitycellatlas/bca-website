// Patch Ghost theme's package.json to expose environment variables via @custom config

const fs = require("fs");

const path = "content.orig/themes/source/package.json";
const j = JSON.parse(fs.readFileSync(path));

j.config = j.config || {};
j.config.custom = j.config.custom || {};
j.config.custom.tracking_script = {
    type: "text",
    default: process.env.PLAUSIBLE_SCRIPT_URL,
};

fs.writeFileSync(path, JSON.stringify(j, null, 2));

console.log("package.json patched");
