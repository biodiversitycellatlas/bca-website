# checkov:skip=CKV_DOCKER_2 "Healthcheck should come from Ghost"
# checkov:skip=CKV_DOCKER_3 "Skip user check"

FROM docker.io/ghost:6.47-alpine

# Build argument for Plausible URL
ARG PLAUSIBLE_SCRIPT_URL
ENV PLAUSIBLE_SCRIPT_URL=${PLAUSIBLE_SCRIPT_URL}

# Patch package.json using environment variables
COPY ghost-env-vars.js /ghost-env-vars.js
RUN node /ghost-env-vars.js
