# syntax=docker/dockerfile:1
# ConfPilot: one image, the FastAPI service plus the built phone app.
# Build from the repo root; the ignore file is deploy/Dockerfile.dockerignore.
#   docker build --platform linux/amd64 -f deploy/Dockerfile -t confpilot:dev .

ARG NODE_VERSION=22
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.11.8
ARG PNPM_VERSION=11.9.0

# --- web: build the Vite app. Runs on the build machine's architecture, because the
# output is static files.
FROM --platform=$BUILDPLATFORM node:${NODE_VERSION}-bookworm-slim AS web
ARG PNPM_VERSION
ENV CI=true
RUN npm install --global --no-fund --no-audit pnpm@${PNPM_VERSION}
WORKDIR /src/web
COPY web/package.json web/pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && pnpm install --frozen-lockfile
# contracts/ sits beside web/ so imports of ../contracts resolve as they do in the repo.
COPY contracts/ /src/contracts/
COPY web/ ./
RUN pnpm build

# --- uv binary, pinned
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# --- api: resolve the locked dependencies into /app/.venv
FROM python:${PYTHON_VERSION}-slim-bookworm AS api
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY api/pyproject.toml api/uv.lock ./
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY api/ ./
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- runtime: same Python base, no build tools, non-root
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --home-dir /app --shell /usr/sbin/nologin app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STATIC_DIR=/app/static \
    PORT=8000
WORKDIR /app
COPY --from=api /app /app
COPY --from=web /src/web/dist /app/static
USER 10001:10001
EXPOSE 8000
# One process: the room hub is in memory, so no --workers. Sockets that outlive a
# SIGTERM are cut after 10 s so a rollout never hangs on an open WebSocket.
CMD ["uvicorn", "confpilot.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-graceful-shutdown", "10"]
