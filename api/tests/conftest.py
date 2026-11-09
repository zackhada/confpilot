"""Shared fixtures. Telemetry goes to in-memory exporters so tests can assert on it."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from confpilot.app import create_app
from confpilot.glossary import SAMPLE_GLOSSARY
from confpilot.settings import Settings

_spans = InMemorySpanExporter()
_metrics = InMemoryMetricReader()
_tracer_provider = TracerProvider()
_tracer_provider.add_span_processor(SimpleSpanProcessor(_spans))
trace.set_tracer_provider(_tracer_provider)
metrics.set_meter_provider(MeterProvider(metric_readers=[_metrics]))


@pytest.fixture
def spans() -> Iterator[InMemorySpanExporter]:
    _spans.clear()
    yield _spans


@pytest.fixture
def metric_reader() -> InMemoryMetricReader:
    _metrics.get_metrics_data()  # drain what earlier tests recorded
    return _metrics


@pytest.fixture
def make_settings() -> Callable[..., Settings]:
    def _make(**overrides: object) -> Settings:
        # Tests pin the small contracts sample, whose term ids never change.
        return Settings(_env_file=None, **{"glossary_path": SAMPLE_GLOSSARY} | overrides)

    return _make


@pytest.fixture
def client(make_settings: Callable[..., Settings]) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings())) as test_client:
        yield test_client
