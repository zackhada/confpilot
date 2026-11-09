"""Deepgram: mint a short-lived token and build the streaming URL the phone connects to.

The browser opens ``ws_url`` with ``new WebSocket(ws_url, ["bearer", token])``. Browsers cannot
set an Authorization header on a WebSocket, so the token travels in Sec-WebSocket-Protocol.
The token only has to be valid when the socket opens; the stream outlives it.
"""

from collections.abc import Iterable
from urllib.parse import quote, urlencode

import httpx

from confpilot.models import Term

GRANT_URL = "https://api.deepgram.com/v1/auth/grant"
LISTEN_URL = "wss://api.deepgram.com/v1/listen"
GRANT_TIMEOUT_S = 5.0
MAX_TTL_S = 3600

# Deepgram allows 500 tokens of keyterms per request and suggests 20 to 50 terms.
# Its tokenizer is not public, so the budget is a deliberately pessimistic estimate.
MAX_KEYTERMS = 50
KEYTERM_TOKEN_BUDGET = 400
MUST_CATCH = ("SRE", "RAG", "embed", "BM25", "RRF", "Elasticsearch", "Kubernetes")


class DeepgramError(Exception):
    """The grant call failed. The message is safe to show to a client."""


def _estimated_tokens(keyterm: str) -> int:
    return sum(1 + len(word) // 2 for word in keyterm.split())


def choose_keyterms(terms: Iterable[Term]) -> list[str]:
    """Must-catch terms first, then the glossary from most to least specialist.

    Common words that are only jargon in context (``ambiguous``) are left out: boosting
    "service" would not help and uses up the budget.
    """
    by_level = sorted((t for t in terms if not t.ambiguous), key=lambda t: -t.level)
    chosen: list[str] = []
    seen: set[str] = set()
    budget = KEYTERM_TOKEN_BUDGET
    for keyterm in (*MUST_CATCH, *(t.term for t in by_level)):
        cost = _estimated_tokens(keyterm)
        if keyterm.casefold() in seen or cost > budget:
            continue
        seen.add(keyterm.casefold())
        chosen.append(keyterm)
        budget -= cost
        if len(chosen) == MAX_KEYTERMS:
            break
    return chosen


def listen_url(keyterms: Iterable[str]) -> str:
    params = [
        ("model", "nova-3"),
        ("encoding", "linear16"),
        ("sample_rate", "16000"),
        ("interim_results", "true"),
        ("punctuate", "false"),
        *(("keyterm", keyterm) for keyterm in keyterms),
    ]
    return f"{LISTEN_URL}?{urlencode(params, quote_via=quote)}"


async def grant_token(client: httpx.AsyncClient, api_key: str, ttl_s: int) -> tuple[str, int]:
    """Return (token, expires_in_s). Never put the API key in an error or a log line."""
    ttl_s = max(1, min(ttl_s, MAX_TTL_S))
    try:
        response = await client.post(
            GRANT_URL,
            headers={"Authorization": f"Token {api_key}"},
            json={"ttl_seconds": ttl_s},
            timeout=GRANT_TIMEOUT_S,
        )
    except httpx.HTTPError as exc:
        raise DeepgramError(f"Could not reach Deepgram ({type(exc).__name__})") from exc
    if response.status_code != httpx.codes.OK:
        raise DeepgramError(f"Deepgram refused the token request (HTTP {response.status_code})")
    try:
        body = response.json()
        return str(body["access_token"]), round(float(body.get("expires_in", ttl_s)))
    except (ValueError, KeyError, TypeError) as exc:
        raise DeepgramError("Deepgram sent a token response we could not read") from exc
