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


def test_blank_env_values_count_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATIC_DIR", "")
    monkeypatch.setenv("DEEPGRAM_API_KEY", " ")

    settings = Settings(_env_file=None)

    assert settings.static_dir is None
    assert settings.deepgram_api_key is None


def test_secrets_are_not_printed(make_settings) -> None:
    settings = make_settings(
        deepgram_api_key="hidden-dg", llm_api_key="hidden-llm", session_secret="hidden-session"
    )

    assert "hidden" not in repr(settings)


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
