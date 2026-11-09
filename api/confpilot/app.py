"""Application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from confpilot.auth import SessionSigner
from confpilot.glossary import load_glossary
from confpilot.http import close_http_client
from confpilot.logsafe import install_session_masking
from confpilot.matching import Matcher
from confpilot.ratelimit import RateLimiter
from confpilot.rooms import Hub
from confpilot.routes import glossary, health, knowledge, session, token, ws
from confpilot.settings import Settings
from confpilot.static import add_static_routes
from confpilot.store import MemoryStore, Store
from confpilot.telemetry import setup_telemetry
from confpilot.utterances import RecentFinals


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_http_client(app)


def create_app(
    settings: Settings | None = None,
    store: Store | None = None,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build the app. ``store`` and ``http_transport`` are the seams for Elasticsearch and tests."""
    settings = settings or Settings()
    setup_telemetry(settings.app_version)
    install_session_masking()

    app = FastAPI(title="ConfPilot API", version=settings.app_version, lifespan=_lifespan)
    app.state.settings = settings
    app.state.glossary = load_glossary(settings.glossary_path)
    app.state.matcher = Matcher(app.state.glossary.terms)
    app.state.store = store or MemoryStore()
    app.state.hub = Hub()
    app.state.recent_finals = RecentFinals()
    app.state.http_transport = http_transport  # used by confpilot.http.http_client
    app.state.signer = SessionSigner.from_setting(settings.session_secret, settings.session_ttl_s)
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
    origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    app.state.allowed_origins = frozenset(origins)
    if origins:  # a web dev server on another origin; in production the API serves the app
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["authorization", "content-type"],
        )
    app.include_router(health.router)
    app.include_router(glossary.router)
    app.include_router(session.router)
    app.include_router(knowledge.router)
    app.include_router(token.router)
    app.include_router(ws.router)

    if settings.static_dir is not None:
        add_static_routes(app, settings.static_dir)  # last: it is a catch-all

    # A room socket lives for a whole talk, so one server span per connection would be useless.
    # The WebSocket handler opens its own short span per event instead.
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/ws/")
    return app
