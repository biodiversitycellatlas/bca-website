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
COPY --from=bun /usr/local/bin/bun* /usr/bin/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=postgres  /opt/postgresql/18/bin/* /usr/bin/
COPY --from=postgres /opt/postgresql/18/lib/libpq.so* /usr/lib/
WORKDIR /usr/src/app
COPY . .
ARG DJANGO_DEPENDENCIES=".[dev,test]"
ENV DJANGO_DEPENDENCIES=${DJANGO_DEPENDENCIES}
# Install Python dependencies
RUN pip install ${DJANGO_DEPENDENCIES} --no-cache-dir .
# Install JavaScript and CSS dependencies
#COPY --from=bun /usr/local/bin/bun* /usr/bin/
#RUN bun install
#RUN bun run build
# Fix permissions for nginx when creating this folder in Django
#RUN chmod go+rx static
# Collect all Django static files
#CMD ["python", "manage.py", "collectstatic", "--noinput"]

FROM dhi.io/python:3.13.13-debian13 as prod
LABEL maintainer="Biodiversity Cell Atlas <bca@biodiversitycellatlas.org>" \
      description="Biodiversity Cell Atlas website and data portal"
# Copy binaries and dependencies from other container images
COPY --from=bun /usr/local/bin/bun* /usr/bin/
COPY --from=diamond /usr/local/bin/diamond /usr/bin/
COPY --from=postgres  /opt/postgresql/18/bin/* /usr/bin/
COPY --from=postgres /opt/postgresql/18/lib/libpq.so* /usr/lib/
COPY --from=dev /usr/bin/bash /usr/bin/
COPY --from=dev /usr/bin/curl /usr/bin/
COPY --from=dev /usr/bin/find /usr/bin/
COPY --from=dev /usr/bin/git /usr/bin/
COPY --from=dev /usr/bin/grep /usr/bin/
COPY --from=dev /lib/x86_64-linux-gnu/libpcre2-8*  /lib/x86_64-linux-gnu/
COPY --from=dev /lib/x86_64-linux-gnu/libgssapi_krb5*  /lib/x86_64-linux-gnu/
COPY --from=dev /opt/python-3.13.13/lib/python3.13/site-packages  /opt/python-3.13.13/lib/python3.13/
#COPY --from=dev /opt/python-3.13.13/bin/coverage* /opt/python-3.13.13/bin/
COPY --from=dev /opt/python-3.13.13/bin/gunicorn* /opt/python-3.13.13/bin/
WORKDIR /usr/src/app
COPY --from=dev /usr/src/app/ .
# Switch to non-root user
#RUN useradd -m bca \
#    && chown -R bca:bca /usr/src/app
#USER bca
SHELL ["/usr/bin/bash", "-o", "pipefail", "-c"]
HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
