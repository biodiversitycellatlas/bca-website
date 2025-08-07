# Get postgreSQL client from official Docker image
FROM postgres:17.5 AS postgres

# Get diamond aligner from biocontainers
FROM buchfink/diamond:version2.1.12 AS diamond

# Serve website
FROM python:3.13

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Copy binaries and dependencies
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=postgres /usr/lib/postgresql/*/bin/ /usr/bin/
COPY --from=postgres /usr/lib/*/libpq.so.5* /usr/lib/aarch64-linux-gnu/
RUN ldconfig

# Switch to non-root user
RUN useradd -m bca \
    && chown -R bca:bca /usr/src/app
USER bca

HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
