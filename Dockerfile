# Get postgreSQL client
FROM dhi.io/postgres:18.4-debian13-dev AS postgres

# Get diamond aligner
FROM buchfink/diamond:version2.1.24 AS diamond

# Get bun
FROM dhi.io/bun:1-debian13-dev AS bun

# Builder and development
FROM  dhi.io/python:3.13.13-debian13-dev AS dev

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=8.14.1-2+deb13u2 \
    dpkg-dev=1.22.22 \
    git=1:2.47.3-0+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

# Copy tools and libraries
COPY --from=bun /usr/local/bin/bun* /usr/bin/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=postgres  /opt/postgresql/18/bin/* /usr/bin/
COPY --from=postgres /opt/postgresql/18/lib/libpq.so* /usr/lib/
RUN arch="$(dpkg-architecture -qDEB_HOST_MULTIARCH)" && \
    cp -a /usr/lib/${arch}/libpcre2* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libselinux* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libbrotlicommon* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libbrotlidec* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libcom_err* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libgnutls* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libgssapi_krb5* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libhogweed* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libidn2* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libk5crypto* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libkeyutils* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libkrb5* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libkrb5support* /usr/lib/ && \
    cp -a /usr/lib/${arch}/liblber* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libldap* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libnettle* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libnghttp2* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libnghttp3* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libp11-kit* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libpsl* /usr/lib/ && \
    cp -a /usr/lib/${arch}/librtmp* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libsasl2* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libssh2* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libtasn1* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libunistring* /usr/lib/ && \
    cp -a /usr/lib/${arch}/libcurl* /usr/lib/ && \
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
COPY --from=dev /usr/lib/libbrotlicommon* /usr/lib/
COPY --from=dev /usr/lib/libbrotlidec* /usr/lib/
COPY --from=dev /usr/lib/libcom_err* /usr/lib/
COPY --from=dev /usr/lib/libcurl* /usr/lib/
COPY --from=dev /usr/lib/libgnutls* /usr/lib/
COPY --from=dev /usr/lib/libgssapi_krb5* /usr/lib/
COPY --from=dev /usr/lib/libhogweed* /usr/lib/
COPY --from=dev /usr/lib/libidn2* /usr/lib/
COPY --from=dev /usr/lib/libk5crypto* /usr/lib/
COPY --from=dev /usr/lib/libkeyutils* /usr/lib/
COPY --from=dev /usr/lib/libkrb5* /usr/lib/
COPY --from=dev /usr/lib/libkrb5support* /usr/lib/
COPY --from=dev /usr/lib/liblber* /usr/lib/
COPY --from=dev /usr/lib/libldap* /usr/lib/
COPY --from=dev /usr/lib/libnettle* /usr/lib/
COPY --from=dev /usr/lib/libnghttp2* /usr/lib/
COPY --from=dev /usr/lib/libnghttp3* /usr/lib/
COPY --from=dev /usr/lib/libp11-kit* /usr/lib/
COPY --from=dev /usr/lib/libpcre2*  /usr/lib/
COPY --from=dev /usr/lib/libpsl* /usr/lib/
COPY --from=dev /usr/lib/librtmp* /usr/lib/
COPY --from=dev /usr/lib/libsasl2* /usr/lib/
COPY --from=dev /usr/lib/libselinux*  /usr/lib/
COPY --from=dev /usr/lib/libssh2* /usr/lib/
COPY --from=dev /usr/lib/libtasn1* /usr/lib/
COPY --from=dev /usr/lib/libunistring* /usr/lib/

# Copy Python packages
COPY --from=dev /opt/python/ /opt/python/

SHELL ["/usr/bin/bash", "-o", "pipefail", "-c"]
HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1
EXPOSE 8000
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000"]
