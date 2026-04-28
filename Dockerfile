# checkov:skip=CKV_DOCKER_3 "Skipping temporarily"

# Get postgreSQL client
FROM dhi.io/postgres:18-debian13-dev AS postgres

# Get diamond aligner
FROM buchfink/diamond:version2.1.24 AS diamond

# Get bun
FROM dhi.io/bun:1-debian13-dev AS bun

# Builder and development
FROM  dhi.io/python:3.13.13-debian13-dev as dev
# Install dependencies
RUN apt-get  update  && apt-get install -y --no-install-recommends \
    curl=8.14.1-2+deb13u2 \
    git=1:2.47.3-0+deb13u1
# Copy tools
COPY --from=bun /usr/local/bin/bun* /usr/bin/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
WORKDIR /usr/src/app
COPY --chown=nonroot:nonroot . .
# Install Python dependencies
ARG DJANGO_DEPENDENCIES=".[dev,test]"
ENV DJANGO_DEPENDENCIES=${DJANGO_DEPENDENCIES}
RUN pip install ${DJANGO_DEPENDENCIES} --no-cache-dir .
# Install frontend dependencies and prepare files
CMD ["chmod", "go+rx", "static"]
CMD ["bun", "install"]
CMD ["bun", "run", "build"]
CMD ["python", "manage.py", "collectstatic", "--noinput"]

# Production image
FROM dhi.io/python:3.13.13-debian13 as prod
LABEL maintainer="Biodiversity Cell Atlas <bca@biodiversitycellatlas.org>" \
      description="Biodiversity Cell Atlas website and data portal"
# Copy binaries and dependencies from other container images
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=dev /usr/bin/bash /usr/bin/
COPY --from=dev /usr/bin/curl /usr/bin/
COPY --from=dev /usr/bin/find /usr/bin/
COPY --from=dev /usr/bin/git /usr/bin/
COPY --from=dev /usr/bin/grep /usr/bin/
# Python packages
COPY --from=dev /opt/python-3.13.13/lib/python3.13/site-packages  /opt/python-3.13.13/lib/python3.13/
COPY --from=dev /opt/python-3.13.13/bin/gunicorn* /opt/python-3.13.13/bin/
WORKDIR /usr/src/app
COPY --from=dev --chown=nonroot:nonroot /usr/src/app/ .
SHELL ["/usr/bin/bash", "-o", "pipefail", "-c"]
HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
