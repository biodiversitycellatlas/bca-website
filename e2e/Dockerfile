# Playwright E2E test runner

# Playwright version must match the browser binaries in the image
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /code

COPY e2e/requirements.txt requirements.txt

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN PLAYWRIGHT_VERSION=$(grep driverVersion /ms-playwright/.docker-info | grep -Eo "[0-9.]+") \
    && pip install --no-cache-dir -r requirements.txt playwright==${PLAYWRIGHT_VERSION}

USER pwuser

HEALTHCHECK NONE
