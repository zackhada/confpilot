# syntax=docker/dockerfile:1
# ConfPilot API image.
#
# Build context = repository root (the parent of deploy/):
#     docker build -t confpilot-api:latest -f deploy/Dockerfile .
#
# The FastAPI app lives at ../app relative to this file:
#   app/main.py          -> exposes `app` (ASGI application)
#   app/requirements.txt -> python deps (must include fastapi + uvicorn)

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so code-only changes reuse this layer.
COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application source (main.py exposes `app`).
COPY app/ ./

# Run as a non-root user so k8s `runAsNonRoot: true` is satisfied.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app
USER app

EXPOSE 8000

# Probes in the k8s manifests hit GET /healthz (served by the app).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
