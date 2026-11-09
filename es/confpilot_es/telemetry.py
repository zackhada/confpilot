"""OpenTelemetry spans around every Elasticsearch call (API only; the app owns the SDK)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from elasticsearch import ApiError, TransportError
from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind

_tracer = trace.get_tracer("confpilot.es")

AttributeValue = str | int | float | bool | None


class EsStoreError(RuntimeError):
    """An Elasticsearch call failed. The message names the operation and the cause."""


def _describe(exc: ApiError | TransportError) -> str:
    if isinstance(exc, ApiError):
        error = exc.body.get("error") if isinstance(exc.body, dict) else None
        reason = error.get("reason") if isinstance(error, dict) else None
        return f"HTTP {exc.status_code}: {reason or exc.message}"
    return f"{type(exc).__name__}: {exc}"


@contextmanager
def es_span(name: str, **attributes: AttributeValue) -> Iterator[Span]:
    """Open a client span named e.g. `es.percolate` with `confpilot.*` attributes.

    Elasticsearch errors are recorded on the span and re-raised as `EsStoreError`.
    """
    with _tracer.start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute("db.system.name", "elasticsearch")
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(f"confpilot.{key}", value)
        try:
            yield span
        except (ApiError, TransportError) as exc:
            raise EsStoreError(f"{name} failed: {_describe(exc)}") from exc
