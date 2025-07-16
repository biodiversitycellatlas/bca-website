FROM python:3.13

# Install postgresql-client 17 from official repo and diamond-aligner
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget gnupg2 lsb-release \
    && wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
            postgresql-client-17 \
            diamond-aligner \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .

# Avoid non-root user
RUN useradd -m bca
RUN chown -R bca:bca /usr/src/app
USER bca

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
