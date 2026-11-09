import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from confpilot.settings import Settings
from confpilot.telemetry import enabled_signals, setup_telemetry


def test_healthz_returns_health_and_opens_a_span(client: TestClient, spans) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    names = [s.name for s in spans.get_finished_spans()]
    assert "healthz" in names


def test_healthz_answers_head_for_uptime_probes(client: TestClient) -> None:
    response = client.head("/healthz")

    assert response.status_code == 200
    assert response.text == ""


def test_blank_env_values_count_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATIC_DIR", "")
    monkeypatch.setenv("DEEPGRAM_API_KEY", " ")

    settings = Settings(_env_file=None)

    assert settings.static_dir is None
    assert settings.deepgram_api_key is None


def test_secrets_are_not_printed(make_settings) -> None:
    settings = make_settings(deepgram_api_key="dg-secret", llm_api_key="llm-secret")

    assert "secret" not in repr(settings)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, ()),
        ({"OTEL_EXPORTER_OTLP_ENDPOINT": ""}, ()),
        ({"OTEL_EXPORTER_OTLP_ENDPOINT": "http://c:4318"}, ("traces", "metrics", "logs")),
        ({"OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": "http://c:4318/v1/metrics"}, ("metrics",)),
        ({"OTEL_EXPORTER_OTLP_ENDPOINT": "http://c:4318", "OTEL_SDK_DISABLED": "true"}, ()),
    ],
)
def test_enabled_signals(env: dict[str, str], expected: tuple[str, ...]) -> None:
    assert enabled_signals(env) == expected


def test_telemetry_is_a_noop_without_an_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("", "_TRACES", "_METRICS", "_LOGS"):
        monkeypatch.delenv(f"OTEL_EXPORTER_OTLP{name}_ENDPOINT", raising=False)

    assert setup_telemetry("test") == ()


def test_telemetry_wires_all_three_signals_when_an_endpoint_is_set() -> None:
    """Runs the production path in a fresh interpreter, because the OpenTelemetry providers
    are process-wide and the test session has already installed in-memory ones."""
    script = """
import os
from opentelemetry import metrics, trace
from opentelemetry._logs import get_logger_provider
from confpilot.telemetry import setup_telemetry

signals = setup_telemetry("test")
providers = (trace.get_tracer_provider(), metrics.get_meter_provider(), get_logger_provider())
print(signals, [type(p).__module__.split(".")[1] for p in providers], flush=True)
os._exit(0)  # skip the exporters' flush at exit: nothing listens on that port
"""
    api_root = Path(__file__).resolve().parents[1]
    env = {
        **{k: v for k, v in os.environ.items() if not k.startswith("OTEL_")},
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:9",
        "PYTHONPATH": str(api_root),
    }

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=120
    )

    assert result.returncode == 0, result.stderr
    assert "('traces', 'metrics', 'logs') ['sdk', 'sdk', 'sdk']" in result.stdout
