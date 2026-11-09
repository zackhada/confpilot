from fastapi import APIRouter, Request, Response

from confpilot.models import SessionRequest, SessionResponse
from confpilot.ratelimit import enforce_rate_limit
from confpilot.telemetry import tracer

router = APIRouter(prefix="/api")


@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: Request, response: Response, body: SessionRequest
) -> SessionResponse:
    """Start a session. The server chooses the user id; the client only chooses a name."""
    enforce_rate_limit(request, "session")
    with tracer.start_as_current_span("session.create") as span:
        user_id, session, expires_at = request.app.state.signer.issue()
        span.set_attribute("confpilot.user_id", user_id)
        response.headers["Cache-Control"] = "no-store"
        return SessionResponse(user_id=user_id, session=session, expires_at=expires_at)
