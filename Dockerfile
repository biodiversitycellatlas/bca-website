FROM python:3.13

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install diamond-aligner
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
            diamond-aligner=2.1.3-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Switch to non-root user
RUN useradd -m bca \
    && chown -R bca:bca /usr/src/app
USER bca

HEALTHCHECK --interval=120s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
