import logging

from fastapi import APIRouter, HTTPException, Request, Response

from confpilot.auth import CurrentUser, require_same_user
from confpilot.deepgram import DeepgramError, choose_keyterms, grant_token, listen_url
from confpilot.http import http_client
from confpilot.models import TokenRequest, TokenResponse
from confpilot.ratelimit import enforce_rate_limit
from confpilot.settings import Settings
from confpilot.telemetry import tracer

NOT_CONFIGURED = "Speech-to-text is not configured: DEEPGRAM_API_KEY is not set on the server"

router = APIRouter(prefix="/api")
_log = logging.getLogger(__name__)


@router.post("/token", response_model=TokenResponse)
async def mint_token(
    request: Request, response: Response, body: TokenRequest, user: CurrentUser
) -> TokenResponse:
    """Mint a short-lived speech-to-text token. The real key never reaches the browser."""
    require_same_user(body.user_id, user)
    enforce_rate_limit(request, "token", user)
    settings: Settings = request.app.state.settings
    attributes = {"confpilot.user_id": body.user_id, "confpilot.stt.provider": "deepgram"}
    with tracer.start_as_current_span("token.mint", attributes=attributes) as span:
        if settings.deepgram_api_key is None:
            raise HTTPException(status_code=503, detail=NOT_CONFIGURED)
        keyterms = choose_keyterms(request.app.state.glossary.terms)
        span.set_attribute("confpilot.stt.keyterm_count", len(keyterms))
        try:
            token, expires_in_s = await grant_token(
                http_client(request.app),
                settings.deepgram_api_key.get_secret_value(),
                settings.deepgram_token_ttl_s,
            )
        except DeepgramError as exc:
            _log.error("token grant failed: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        response.headers["Cache-Control"] = "no-store"
        return TokenResponse(token=token, expires_in_s=expires_in_s, ws_url=listen_url(keyterms))
