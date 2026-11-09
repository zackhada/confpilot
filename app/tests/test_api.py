"""Endpoint smoke tests that do not require Elasticsearch or an LLM."""
from __future__ import annotations


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "confpilot"
    assert data["status"] in ("ok", "degraded")
    assert set(data["dependencies"]) == {"elasticsearch", "llm"}


def test_search_degrades_gracefully_without_es(client):
    resp = client.get("/api/search", params={"q": "ebpf security"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["hits"] == []


def test_search_requires_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 422


def test_match_requires_interests_or_vector(client):
    resp = client.post("/api/match", json={})
    assert resp.status_code == 422


def test_rooms_returns_quiet_room(client):
    resp = client.get("/api/rooms")
    assert resp.status_code == 200
    rooms = resp.json()["rooms"]
    assert isinstance(rooms, list) and rooms
    names = [r["name"] for r in rooms]
    assert "Quiet Room" in names
    for r in rooms:
        assert r["crowd_level"] in ("low", "medium", "high", "full", "unknown")


def test_chaos_state_roundtrip(client):
    assert client.get("/api/chaos").json()["enabled"] is False
    resp = client.post("/api/chaos", json={"enabled": True, "latency_ms": 250, "error_rate": 0.5})
    assert resp.status_code == 200
    state = resp.json()
    assert state["enabled"] is True
    assert state["latency_ms"] == 250
    assert state["error_rate"] == 0.5
    # clean up
    client.post("/api/chaos", json={"enabled": False})
    assert client.get("/api/chaos").json()["enabled"] is False


def test_chaos_injects_errors_but_exempts_ops(client):
    client.post("/api/chaos", json={"enabled": True, "error_rate": 1.0, "latency_ms": 0})
    try:
        assert client.get("/api/search", params={"q": "x"}).status_code == 503
        # exempt endpoints stay usable so chaos can be turned off
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/chaos").status_code == 200
    finally:
        client.post("/api/chaos", json={"enabled": False})


def test_frontend_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ConfPilot" in resp.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
