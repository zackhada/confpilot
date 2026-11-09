# syntax=docker/dockerfile:1
# ConfPilot: one image, the FastAPI service plus the built phone app.
# Build from the repo root; the ignore file is deploy/Dockerfile.dockerignore.
#   docker build --platform linux/amd64 -f deploy/Dockerfile -t confpilot:dev .
#
# Layout in the image mirrors the repo, so a path dependency from api/ on ../es resolves:
#   /app/api      the service and its virtualenv (working directory)
#   /app/es       the es/ package, once it exists
#   /app/content  glossary.json (GLOSSARY_PATH)
#   /app/static   the built web app (STATIC_DIR); empty until web/ exists

ARG NODE_VERSION=22
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.11.8
ARG PNPM_VERSION=11.9.0

# --- sources: web/ and es/ land on main after this file does. This stage always
# succeeds and hands the later stages a directory that exists either way. It reruns on any
# change to the build context, but it is only a copy; the stages below are cached on the
# content of the directory they take from it.
FROM python:${PYTHON_VERSION}-slim-bookworm AS sources
RUN --mount=type=bind,target=/ctx \
    mkdir -p /out/web /out/es \
    && if [ -d /ctx/web ]; then cp -a /ctx/web/. /out/web/; fi \
    && if [ -d /ctx/es ]; then cp -a /ctx/es/. /out/es/; fi

# --- web: build the Vite app. Runs on the build machine's architecture, because the
# output is static files.
FROM --platform=$BUILDPLATFORM node:${NODE_VERSION}-bookworm-slim AS web
ARG PNPM_VERSION
ENV CI=true
RUN npm install --global --no-fund --no-audit pnpm@${PNPM_VERSION}
# contracts/ sits beside web/ so imports of ../contracts resolve as they do in the repo.
COPY contracts/ /src/contracts/
COPY content/glossary.json /src/content/glossary.json
WORKDIR /src/web
COPY --from=sources /out/web/ ./
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    if [ -f package.json ]; then \
        pnpm config set store-dir /pnpm/store \
        && pnpm install --frozen-lockfile \
        && pnpm build; \
    else \
        echo "web/ is not in the build context: the image ships without the phone app" \
        && mkdir -p dist; \
    fi

# --- uv binary, pinned
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# --- api: resolve the locked dependencies into /app/api/.venv
FROM python:${PYTHON_VERSION}-slim-bookworm AS api
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY --from=sources /out/es/ /app/es/
WORKDIR /app/api
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
ENV PATH=/app/api/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STATIC_DIR=/app/static \
    GLOSSARY_PATH=/app/content/glossary.json
COPY --from=api /app/ /app/
COPY content/glossary.json /app/content/glossary.json
COPY --from=web /src/web/dist/ /app/static/
WORKDIR /app/api
USER 10001:10001
EXPOSE 8000
# One process: the room hub is in memory, so no --workers. Sockets that outlive a
# SIGTERM are cut after 10 s so a rollout never hangs on an open WebSocket.
CMD ["uvicorn", "confpilot.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-graceful-shutdown", "10"]
