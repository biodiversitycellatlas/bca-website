# Playwright E2E test runner

# Playwright version must match the browser binaries in the image
ARG PLAYWRIGHT_VERSION=1.62.0

FROM mcr.microsoft.com/playwright/python:v${PLAYWRIGHT_VERSION}-noble

ARG PLAYWRIGHT_VERSION

WORKDIR /code

COPY e2e/requirements.txt requirements.txt

RUN pip install --no-cache-dir \
    -r requirements.txt \
    playwright==${PLAYWRIGHT_VERSION}
