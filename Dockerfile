# checkov:skip=CKV_DOCKER_3 "Skipping temporarily"

# Get postgreSQL client
FROM postgres:17.6-trixie AS postgres

# Get diamond aligner
FROM buchfink/diamond:version2.1.17 AS diamond

# Get bun
FROM oven/bun:1.3.6-slim AS bun

# Serve website
FROM python:3.13.7-trixie

LABEL maintainer="Biodiversity Cell Atlas <bca@biodiversitycellatlas.org>" \
      description="Biodiversity Cell Atlas website and data portal"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Python dependencies
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Copy binaries and dependencies
COPY --from=postgres /usr/lib/postgresql/*/bin/ /usr/bin/
COPY --from=postgres /usr/lib/*/libpq.so.5* /usr/lib/aarch64-linux-gnu/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=bun /usr/local/bin/bun /usr/bin/
RUN ldconfig

# Install JavaScript and CSS dependencies
RUN bun install

# Switch to non-root user
#RUN useradd -m bca \
#    && chown -R bca:bca /usr/src/app
#USER bca

HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
