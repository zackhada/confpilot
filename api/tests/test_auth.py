import pytest
from fastapi.testclient import TestClient
from helpers import bearer
from starlette.datastructures import Headers

from confpilot.auth import origin_allowed


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"host": "confpilot.example"}, True),  # not a browser
        ({"host": "confpilot.example", "origin": "https://confpilot.example"}, True),
        ({"host": "localhost:8000", "origin": "http://localhost:8000"}, True),
        ({"host": "confpilot.example", "origin": "http://localhost:5173"}, True),  # allow-list
        ({"host": "confpilot.example", "origin": "https://evil.example"}, False),
        ({"host": "confpilot.example", "origin": "https://confpilot.example.evil.io"}, False),
        ({"host": "confpilot.example", "origin": "null"}, False),
        ({"origin": "https://confpilot.example"}, False),
    ],
)
def test_origin_allowed(headers: dict[str, str], expected: bool) -> None:
    allowed = frozenset({"http://localhost:5173"})

    assert origin_allowed(Headers(headers), allowed) is expected


def test_api_routes_need_a_session_except_glossary_and_health(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/glossary").status_code == 200
    for method, path in [
        ("get", "/api/users/u-ana/knowledge"),
        ("put", "/api/users/u-ana/knowledge/rag"),
        ("get", "/api/rooms/slc1/recap"),
        ("get", "/api/search?q=rag&room=slc1"),
    ]:
        response = client.request(method, path, json={})
        assert response.status_code == 401, path
        assert "POST /api/session" in response.json()["detail"]
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer", "Bearer not-a-session", "Basic abc", "abc.def"])
def test_a_bad_authorization_header_is_a_401(client: TestClient, header: str) -> None:
    response = client.get("/api/users/u-ana/knowledge", headers={"Authorization": header})

    assert response.status_code == 401


def test_an_expired_session_is_a_401(client: TestClient) -> None:
    _, session, _ = client.app.state.signer.issue("u-ana", now_ms=0)  # expired in 1970

    response = client.get(
        "/api/users/u-ana/knowledge", headers={"Authorization": f"Bearer {session}"}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_one_user_cannot_read_or_write_another_users_knowledge(client: TestClient) -> None:
    ben = bearer(client, "u-ben")

    read = client.get("/api/users/u-ana/knowledge", headers=ben)
    write = client.put("/api/users/u-ana/knowledge/rag", json={"status": "known"}, headers=ben)

    assert (read.status_code, write.status_code) == (403, 403)
    assert client.app.state.store._knowledge == {}


def test_a_session_from_post_session_opens_the_callers_own_knowledge(client: TestClient) -> None:
    body = client.post("/api/session", json={"name": "Ana"}).json()

    own = client.get(
        f"/api/users/{body['user_id']}/knowledge",
        headers={"Authorization": f"Bearer {body['session']}"},
    )

    assert own.json() == {"items": []}
