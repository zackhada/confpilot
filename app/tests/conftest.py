"""Shared pytest fixtures: isolate ES/LLM config and reset chaos state."""
from __future__ import annotations

import pytest

from confpilot import config, elasticsearch_client
from confpilot.services import chaos


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    """Ensure tests never touch a real Elasticsearch/LLM backend."""
    monkeypatch.setattr(config, "ES_URL", None)
    monkeypatch.setattr(config, "ES_API_KEY", None)
    monkeypatch.setattr(config, "ES_USERNAME", None)
    monkeypatch.setattr(config, "LLM_BASE_URL", None)
    elasticsearch_client.reset()
    chaos.set_state(enabled=False, latency_ms=0, error_rate=0.0)
    yield
    chaos.set_state(enabled=False, latency_ms=0, error_rate=0.0)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from confpilot.main import app

    return TestClient(app)
