"""Chaos engineering toggle: inject latency and errors into the API.

State lives in-process and is controlled via ``/api/chaos``. The middleware
in :func:`chaos_middleware` applies the configured latency/error rate to every
request except a small exempt allow-list (so you can always turn chaos off).
"""
from __future__ import annotations

import asyncio
import random
import threading

from fastapi.responses import JSONResponse
from opentelemetry import metrics, trace

tracer = trace.get_tracer("confpilot.chaos")
meter = metrics.get_meter("confpilot.chaos")

latency_counter = meter.create_counter("confpilot.chaos.latency_injections", "1", "injected latency events")
error_counter = meter.create_counter("confpilot.chaos.error_injections", "1", "injected error responses")

_EXEMPT_PREFIXES = ("/healthz", "/api/chaos", "/static", "/docs", "/redoc", "/openapi.json", "/favicon.ico")

_state: dict = {"enabled": False, "latency_ms": 0, "error_rate": 0.0}
_lock = threading.Lock()


def get_state() -> dict:
    with _lock:
        return dict(_state)


def set_state(
    enabled: bool | None = None,
    latency_ms: int | None = None,
    error_rate: float | None = None,
) -> dict:
    with _lock:
        if enabled is not None:
            _state["enabled"] = bool(enabled)
        if latency_ms is not None:
            _state["latency_ms"] = max(0, int(latency_ms))
        if error_rate is not None:
            _state["error_rate"] = min(1.0, max(0.0, float(error_rate)))
        return dict(_state)


def _is_exempt(path: str) -> bool:
    return path == "/" or any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


async def chaos_middleware(request, call_next):
    """Starlette middleware that injects latency and/or 503 errors."""
    path = request.url.path
    if _is_exempt(path):
        return await call_next(request)

    state = get_state()
    if not state["enabled"]:
        return await call_next(request)

    if state["latency_ms"] > 0:
        latency_counter.add(1)
        with tracer.start_as_current_span("chaos.latency") as span:
            span.set_attributes({"chaos.latency_ms": state["latency_ms"], "chaos.path": path})
            await asyncio.sleep(state["latency_ms"] / 1000.0)

    if state["error_rate"] > 0 and random.random() < state["error_rate"]:
        error_counter.add(1)
        with tracer.start_as_current_span("chaos.error") as span:
            span.set_attributes({"chaos.error_rate": state["error_rate"], "chaos.path": path})
        return JSONResponse(
            status_code=503,
            content={"detail": "Injected error by chaos toggle", "chaos": True},
        )

    return await call_next(request)
