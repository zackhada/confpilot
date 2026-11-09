import asyncio
import logging

from fastapi import APIRouter, Request

from confpilot.auth import CurrentUser, require_same_user
from confpilot.http import http_client
from confpilot.models import ProbeRequest, ProbeResponse
from confpilot.probe import heuristic_probe, llm_probe
from confpilot.ratelimit import enforce_rate_limit
from confpilot.settings import Settings
from confpilot.telemetry import tracer

router = APIRouter(prefix="/api")
_log = logging.getLogger(__name__)


@router.post("/probe", response_model=ProbeResponse)
async def probe(request: Request, body: ProbeRequest, user: CurrentUser) -> ProbeResponse:
    """The only place a client waits on an LLM, so it is time-boxed and always has an answer."""
    require_same_user(body.user_id, user)
    enforce_rate_limit(request, "probe", user)
    state = request.app.state
    settings: Settings = state.settings
    attributes = {
        "confpilot.user_id": user,
        "confpilot.probe.transcript_length": len(body.transcript),
    }
    with tracer.start_as_current_span("probe", attributes=attributes) as span:
        result = heuristic_probe(body.transcript, state.matcher, state.glossary)
        source = "heuristic"
        if settings.llm_api_key is not None:
            try:
                async with asyncio.timeout(settings.probe_timeout_s):
                    answer = await llm_probe(
                        http_client(request.app),
                        base_url=settings.llm_base_url,
                        api_key=settings.llm_api_key.get_secret_value(),
                        model=settings.llm_model,
                        timeout_s=settings.probe_timeout_s,
                        transcript=body.transcript,
                        glossary=state.glossary,
                    )
            except Exception as exc:  # any LLM failure falls back; the phone still gets a profile
                reason = type(exc).__name__
                # The request did not fail, so the span stays OK, but the failure is recorded.
                # Only the exception type goes on the span: an HTTP error's text can echo the
                # upstream response.
                span.add_event("exception", {"exception.type": reason})
                span.set_attribute("confpilot.probe.fallback_reason", reason)
                _log.warning("probe LLM failed (%s), using the heuristic", reason)
            else:
                # Trust the LLM over the heuristic: "I keep hearing about RAG" uses the term
                # without knowing it, and only the LLM can tell.
                result = answer
                source = "llm"
        span.set_attribute("confpilot.probe.source", source)
        span.set_attribute("confpilot.probe.known_count", len(result.known_term_ids))
        return result
