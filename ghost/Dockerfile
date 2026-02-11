FROM ghost:6.4-alpine

# Build argument for Plausible URL
ARG PLAUSIBLE_SCRIPT_URL
ENV PLAUSIBLE_SCRIPT_URL=${PLAUSIBLE_SCRIPT_URL}

# Patch package.json using environment variables
COPY ghost-env-vars.js /ghost-env-vars.js
RUN node /ghost-env-vars.js

