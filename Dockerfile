# checkov:skip=CKV_DOCKER_3 "Skipping temporarily"

# Get postgreSQL client from official Docker image
FROM postgres:17.6-trixie AS postgres

# Serve website
FROM python:3.13.7-trixie

LABEL maintainer="Biodiversity Cell Atlas <bca@biodiversitycellatlas.org>" \
      description="Biodiversity Cell Atlas website and data portal"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
            diamond-aligner=2.1.11-2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Copy binaries and dependencies
COPY --from=postgres /usr/lib/postgresql/*/bin/ /usr/bin/
COPY --from=postgres /usr/lib/*/libpq.so.5* /usr/lib/aarch64-linux-gnu/
RUN ldconfig

# Switch to non-root user
#RUN useradd -m bca \
#    && chown -R bca:bca /usr/src/app
#USER bca

HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
