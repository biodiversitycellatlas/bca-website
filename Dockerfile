# Get postgreSQL client
FROM dhi.io/postgres:18-debian13-dev AS postgres

# Get diamond aligner
FROM buchfink/diamond:version2.1.24 AS diamond

# Get bun
FROM dhi.io/bun:1-debian13-dev AS bun

# Builder and development
FROM  dhi.io/python:3.13.13-debian13-dev AS dev

# Install dependencies
RUN apt-get  update  && apt-get install -y --no-install-recommends \
    curl=8.14.1-2+deb13u2 \
    dpkg-dev=1.22.22 \
    git=1:2.47.3-0+deb13u1

# Copy tools and libraries
COPY --from=bun /usr/local/bin/bun* /usr/bin/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=postgres  /opt/postgresql/18/bin/* /usr/bin/
COPY --from=postgres /opt/postgresql/18/lib/libpq.so* /usr/lib/
RUN arch=$(dpkg-architecture -qDEB_HOST_MULTIARCH) && \
    cp /usr/lib/${arch}/libpcre2* /usr/lib/ && \	
    cp /usr/lib/${arch}/libselinux* /usr/lib/ && \	
    mv /usr/lib/libpq.so* /usr/lib/${arch}/ && \
    ldconfig

# Copy application folder
WORKDIR /usr/src/app
COPY --chown=nonroot:nonroot . .

# Install Python dependencies
ARG DJANGO_DEPENDENCIES=".[dev,test]"
ENV DJANGO_DEPENDENCIES=${DJANGO_DEPENDENCIES}
RUN pip install ${DJANGO_DEPENDENCIES} --no-cache-dir .

# Production image
FROM dhi.io/python:3.13.13-debian13 AS prod
LABEL maintainer="Biodiversity Cell Atlas <bca@biodiversitycellatlas.org>" \
    description="Biodiversity Cell Atlas website and data portal"
USER nonroot

# Copy application folder
WORKDIR /usr/src/app
COPY --from=dev --chown=nonroot:nonroot /usr/src/app/ .

# Copy binaries and dependencies from other container images
COPY --from=bun /usr/local/bin/bun* /usr/bin/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=dev /usr/bin/bash /usr/bin/
COPY --from=dev /usr/bin/chmod /usr/bin/
COPY --from=dev /usr/bin/curl /usr/bin/
COPY --from=dev /usr/bin/find /usr/bin/
COPY --from=dev /usr/bin/git /usr/bin/
COPY --from=dev /usr/bin/grep /usr/bin/
COPY --from=dev /usr/bin/mkdir /usr/bin/
COPY --from=dev /usr/bin/sh /usr/bin/
COPY --from=dev /usr/lib/libpcre2*  /usr/lib/
COPY --from=dev /usr/lib/libselinux*  /usr/lib/

# Copy Python packages
COPY --from=dev /opt/python-3.13.13/lib/python3.13/site-packages  /opt/python-3.13.13/lib/python3.13/
COPY --from=dev /opt/python-3.13.13/bin/gunicorn* /opt/python-3.13.13/bin/

SHELL ["/usr/bin/bash", "-o", "pipefail", "-c"]
HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1
EXPOSE 8000
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000"]
