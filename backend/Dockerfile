FROM python:3.12-slim AS base

ENV FLASK_APP=run.py \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tools are needed for psycopg2 and are removed afterwards to keep
# the runtime image small.
COPY requirements.txt requirements-prod.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl libjpeg62-turbo libwebp7 \
    && pip install --no-cache-dir -r requirements-prod.txt \
    && apt-get purge -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Run as an unprivileged user; the upload directory is the only writable path.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# The port is injected by the platform, so the check reads it rather than
# assuming 5000.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-5000}/api/ready" || exit 1

# Migrations are applied before the workers start, so a container can
# never serve against a schema older than the code it is running.
CMD ["sh", "-c", "flask db upgrade && exec gunicorn -c gunicorn.conf.py run:app"]
