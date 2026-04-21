# checkov:skip=CKV_DOCKER_3 "Skipping temporarily"

# Get postgreSQL client
FROM dhi.io/postgres:18-debian13-dev AS postgres

# Get diamond aligner
FROM buchfink/diamond:version2.1.24 AS diamond

# Get bun
FROM dhi.io/bun:1-debian13-dev AS bun

# Serve website
FROM  dhi.io/python:3.13.12-debian13-dev

LABEL maintainer="Biodiversity Cell Atlas <bca@biodiversitycellatlas.org>" \
      description="Biodiversity Cell Atlas website and data portal"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install dependencies
RUN apt-get  update  && apt-get install -y --no-install-recommends git=1:2.47.3-0+deb13u1
# Install Python dependencies
WORKDIR /usr/src/app
COPY pyproject.toml ./
RUN pip install .[dev,test] --no-cache-dir .
COPY . .

# Copy binaries and dependencies from other container images
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=bun /usr/local/bin/bun* /usr/bin/

COPY --from=postgres  /opt/postgresql/18/bin/* /usr/bin/
COPY --from=postgres /opt/postgresql/18/lib/libpq.so* /usr/lib/


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
