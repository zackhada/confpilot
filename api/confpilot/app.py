"""Application factory."""

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from confpilot.glossary import load_glossary
from confpilot.matching import Matcher
from confpilot.routes import glossary, health
from confpilot.settings import Settings
from confpilot.static import add_static_routes
from confpilot.telemetry import setup_telemetry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    setup_telemetry(settings.app_version)

    app = FastAPI(title="ConfPilot API", version=settings.app_version)
    app.state.settings = settings
    app.state.glossary = load_glossary(settings.glossary_path)
    app.state.matcher = Matcher(app.state.glossary.terms)
    app.include_router(health.router)
    app.include_router(glossary.router)

    if settings.static_dir is not None:
        add_static_routes(app, settings.static_dir)  # last: it is a catch-all

    # A room socket lives for a whole talk, so one server span per connection would be useless.
    # The WebSocket handler opens its own short span per event instead.
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/ws/")
    return app
