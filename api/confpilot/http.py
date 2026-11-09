"""One shared outbound HTTP client (Deepgram, the LLM), created on first use.

Building an httpx client loads the TLS trust store, which is slow enough to notice, so the
app does not pay for it until a route needs it.
"""

import httpx
from fastapi import FastAPI
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


def http_client(app: FastAPI) -> httpx.AsyncClient:
    client: httpx.AsyncClient | None = getattr(app.state, "http", None)
    if client is None:
        client = httpx.AsyncClient(transport=app.state.http_transport)
        HTTPXClientInstrumentor.instrument_client(client)
        app.state.http = client
    return client


async def close_http_client(app: FastAPI) -> None:
    client: httpx.AsyncClient | None = getattr(app.state, "http", None)
    if client is not None:
        app.state.http = None
        await client.aclose()
