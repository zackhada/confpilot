"""ConfPilot FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .elasticsearch_client import es_available
from .routers import api
from .services import chaos
from .services.llm import llm_available
from .telemetry import setup_telemetry, shutdown_telemetry

log = logging.getLogger("confpilot.main")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

setup_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("ConfPilot starting (service=%s version=%s)", config.SERVICE_NAME, config.SERVICE_VERSION)
    yield
    log.info("ConfPilot shutting down; flushing telemetry")
    shutdown_telemetry()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ConfPilot",
        version=config.SERVICE_VERSION,
        description="Accessible AI conference companion (search, RAG, matchmaking, crowd levels).",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Chaos middleware is added before instrumentation so the OTel server span wraps it.
    app.middleware("http")(chaos.chaos_middleware)

    app.include_router(api.router)

    @app.get("/healthz", tags=["ops"], summary="Liveness + dependency status")
    def healthz():
        es_ok = es_available()
        llm_ok = llm_available()
        ok = es_ok and llm_ok
        return {
            "status": "ok" if ok else "degraded",
            "service": config.SERVICE_NAME,
            "version": config.SERVICE_VERSION,
            "dependencies": {
                "elasticsearch": "ok" if es_ok else "unavailable",
                "llm": "ok" if llm_ok else "unavailable",
            },
            "chaos": chaos.get_state(),
        }

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(STATIC_DIR / "index.html")

    # OpenTelemetry FastAPI instrumentation (exclude the health probe from traces).
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz")
    except Exception:  # pragma: no cover - defensive
        log.exception("Failed to instrument FastAPI")

    return app


app = create_app()
