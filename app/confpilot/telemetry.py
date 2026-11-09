"""OpenTelemetry setup: traces, metrics, and logs exported over OTLP/HTTP.

Everything is best-effort: if the OTLP endpoint is missing or the exporters
fail to boot, the app keeps running and telemetry simply is not exported.
"""
from __future__ import annotations

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from . import config

log = logging.getLogger("confpilot.telemetry")

_setup_done = False
_providers: dict = {}


def _endpoint() -> str | None:
    return config.OTEL_EXPORTER_OTLP_ENDPOINT or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")


def _base_endpoint(url: str) -> str:
    """OTLP HTTP exporters append /v1/<signal>; accept either base or signal URL."""
    url = (url or "").rstrip("/")
    for suffix in ("/v1/traces", "/v1/metrics", "/v1/logs"):
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url


def _resource() -> Resource:
    return Resource.create(
        {
            "service.name": config.SERVICE_NAME,
            "service.version": config.SERVICE_VERSION,
            "deployment.environment": config.DEPLOYMENT_ENV,
        }
    )  # Resource.create already merges SDK defaults + OTEL_RESOURCE_ATTRIBUTES


def _setup_traces(resource: Resource, exporter) -> None:
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _providers["trace"] = provider


def _setup_metrics(resource: Resource, exporter) -> None:
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15_000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    _providers["meter"] = provider


def _setup_logs(resource: Resource, exporter) -> None:
    from opentelemetry.sdk._logs import LoggingHandler, LoggerProvider, set_logger_provider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    _providers["logs"] = provider


def _instrument() -> None:
    """Install library instrumentors that do not need the app instance."""
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception:  # pragma: no cover - defensive
        log.exception("Failed to instrument httpx")

    try:
        from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor

        ElasticsearchInstrumentor().instrument()
    except Exception:  # pragma: no cover - defensive
        log.exception("Failed to instrument elasticsearch")

    try:
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        LoggingInstrumentor().instrument(set_logging_format=True)
    except Exception:  # pragma: no cover - defensive
        log.exception("Failed to instrument logging")


def setup_telemetry() -> None:
    """Idempotent global telemetry bootstrap."""
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    resource = _resource()
    endpoint = _endpoint()

    if endpoint:
        base = _base_endpoint(endpoint)
        try:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

            _setup_traces(resource, OTLPSpanExporter(endpoint=base))
            _setup_metrics(resource, OTLPMetricExporter(endpoint=base))
            _setup_logs(resource, OTLPLogExporter(endpoint=base))
            log.info("OTLP exporters configured for %s", base)
        except Exception:  # pragma: no cover - defensive
            log.exception("OTLP exporter setup failed; continuing without export")
    else:
        log.warning("OTEL_EXPORTER_OTLP_ENDPOINT not set; telemetry export is disabled")

    _instrument()


def shutdown_telemetry() -> None:
    """Flush and shut down providers (called from the app lifespan)."""
    for name in ("trace", "meter", "logs"):
        provider = _providers.get(name)
        if provider is not None:
            try:
                provider.shutdown()
            except Exception:  # pragma: no cover - defensive
                log.exception("Failed to shutdown %s provider", name)
