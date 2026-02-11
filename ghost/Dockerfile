FROM ghost:6.4-alpine

# Build argument for Plausible URL
ARG PLAUSIBLE_SCRIPT_URL
ENV PLAUSIBLE_SCRIPT_URL=${PLAUSIBLE_SCRIPT_URL}

# Patch package.json using the build ARG
RUN node <<'EOF'
    // Read package.json
    const fs = require('fs');
    const path = 'content.orig/themes/source/package.json';
    const j = JSON.parse(fs.readFileSync(path));

    // Add PLAUSIBLE_SCRIPT_URL
    j.config.custom = j.config.custom || {};
    j.config.custom.tracking_script = {
        "type": "text",
        "default": process.env.PLAUSIBLE_SCRIPT_URL
    };

    // Write the updated JSON back
    fs.writeFileSync(path, JSON.stringify(j, null, 2));
EOF
