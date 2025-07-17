FROM python:3.13

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install postgresql-client 17 from official repo and diamond-aligner
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
            gnupg2=2.2.40-1.1 \
            lsb-release=12.0-1 \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
            postgresql-client-17=17.5-1.pgdg120+1 \
            diamond-aligner=2.1.3-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Switch to non-root user
RUN useradd -m bca \
    && chown -R bca:bca /usr/src/app
#USER bca

HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
