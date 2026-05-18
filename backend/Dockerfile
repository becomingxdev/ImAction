# ============================================================
# ImAction CKA — Dockerfile (Cloud Run production)
# ============================================================
# Multi-stage build:
#   Stage 1 (builder): install Python deps into a virtual env
#   Stage 2 (runtime): copy only the venv + app source — no build tools
#
# Cloud Run injects PORT, GOOGLE_CLOUD_PROJECT, and all secrets
# as environment variables at runtime; nothing is baked into the image.
# ============================================================

# ---------- Stage 1: dependency builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system libs needed by psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: lean runtime image ----------
FROM python:3.12-slim AS runtime

# Non-root user for security hardening
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# System libs needed at runtime by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY app/ ./app/

# Activate venv for all subsequent commands
ENV PATH="/opt/venv/bin:$PATH"

# Production defaults — all can be overridden via Cloud Run env vars
ENV APP_ENV=production \
    DEBUG=false \
    EMBEDDING_PROVIDER=gemini \
    LLM_PROVIDER=gemini \
    GOOGLE_CLOUD_LOCATION=us-central1 \
    GEMINI_MODEL=gemini-2.0-flash

# Cloud Run injects PORT; default to 8080 for local docker run
ENV PORT=8080

USER appuser

# Use shell form so $PORT is evaluated at runtime
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 60
