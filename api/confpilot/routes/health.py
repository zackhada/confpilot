from fastapi import APIRouter, Request

from confpilot.models import Health
from confpilot.telemetry import tracer

router = APIRouter()


@router.get("/healthz", response_model=Health)
async def healthz(request: Request) -> Health:
    version = request.app.state.settings.app_version
    with tracer.start_as_current_span("healthz", attributes={"confpilot.version": version}):
        return Health(version=version)
