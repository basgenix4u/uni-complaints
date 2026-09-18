FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tools are needed for psycopg2 and are removed afterwards to keep
# the runtime image small.
COPY requirements.txt requirements-prod.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
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

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:5000/api/ready || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
