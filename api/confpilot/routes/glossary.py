from fastapi import APIRouter, Request

from confpilot.models import Glossary
from confpilot.telemetry import tracer

router = APIRouter(prefix="/api")


@router.get("/glossary", response_model=Glossary)
async def get_glossary(request: Request) -> Glossary:
    glossary: Glossary = request.app.state.glossary
    attributes = {
        "confpilot.glossary.version": glossary.version,
        "confpilot.glossary.term_count": len(glossary.terms),
    }
    with tracer.start_as_current_span("glossary.get", attributes=attributes):
        return glossary
