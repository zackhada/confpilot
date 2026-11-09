"""OpenTelemetry: traces, metrics and logs over OTLP/HTTP.

Everything is driven by the standard ``OTEL_EXPORTER_OTLP_*`` environment variables, which the
exporters read themselves (endpoint, headers, timeout). When no endpoint is set, setup is a
no-op: code still calls the OTel API through ``tracer`` and ``meter``, and it costs nothing.
"""

import logging
import os
from collections.abc import Mapping

from opentelemetry import metrics, trace

DEFAULT_SERVICE_NAME = "confpilot-api"
SIGNALS = ("traces", "metrics", "logs")
# 800 ms is the SLO threshold, so it has to be a bucket boundary.
LATENCY_BUCKETS_MS = (50, 100, 200, 300, 400, 500, 600, 700, 800, 1000, 1500, 2000, 3000, 5000)

tracer = trace.get_tracer("confpilot.api")
meter = metrics.get_meter("confpilot.api")
word_to_card_ms = meter.create_histogram(
    "confpilot.card.word_to_card_ms",
    unit="ms",
    description="Time from the end of a spoken word to its card being rendered",
    explicit_bucket_boundaries_advisory=LATENCY_BUCKETS_MS,
)

_log = logging.getLogger(__name__)
_configured = False


def enabled_signals(env: Mapping[str, str]) -> tuple[str, ...]:
    """Signals that have an OTLP endpoint, either the shared one or their own."""
    if env.get("OTEL_SDK_DISABLED", "").lower() == "true":
        return ()
    shared = bool(env.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
    return tuple(
        s for s in SIGNALS if shared or env.get(f"OTEL_EXPORTER_OTLP_{s.upper()}_ENDPOINT")
    )


def setup_telemetry(version: str) -> tuple[str, ...]:
    """Install the SDK providers once. Returns the signals that are being exported."""
    global _configured
    signals = enabled_signals(os.environ)
    if not signals or _configured:
        return signals
    _configured = True

    from opentelemetry.sdk.resources import Resource

    attributes = {"service.version": version}
    declared = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
    if not os.environ.get("OTEL_SERVICE_NAME") and "service.name=" not in declared:
        attributes["service.name"] = DEFAULT_SERVICE_NAME
    resource = Resource.create(attributes)

    if "traces" in signals:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

    if "metrics" in signals:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    if "logs" in signals:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(logger_provider)
        root = logging.getLogger()
        root.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))
        if root.level in (logging.NOTSET, logging.WARNING):
            root.setLevel(logging.INFO)

    _log.info("telemetry enabled", extra={"confpilot.otel.signals": ",".join(signals)})
    return signals
