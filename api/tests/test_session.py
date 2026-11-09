import base64
import json
import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from confpilot.app import create_app
from confpilot.auth import SESSION_TTL_S, SessionSigner
from confpilot.ratelimit import RateLimiter

NOW = 1_800_000_000_000


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def test_session_round_trip_and_expiry() -> None:
    signer = SessionSigner(b"k" * 32)

    user_id, session, expires_at = signer.issue(now_ms=NOW)

    assert uuid.UUID(user_id).version == 4
    assert expires_at == NOW + SESSION_TTL_S * 1000
    assert signer.verify(session, now_ms=NOW) == user_id
    assert signer.verify(session, now_ms=expires_at - 1) == user_id
    assert signer.verify(session, now_ms=expires_at) is None


def test_session_is_payload_dot_hmac_and_cannot_be_forged() -> None:
    signer = SessionSigner(b"k" * 32)
    _, session, _ = signer.issue("u-ana", now_ms=NOW)
    payload, signature = session.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    forged_payload = b64(json.dumps({"user_id": "u-ben", "exp": claims["exp"]}).encode())

    assert claims == {"user_id": "u-ana", "exp": NOW + SESSION_TTL_S * 1000}
    assert signer.verify(f"{forged_payload}.{signature}", now_ms=NOW) is None  # other user
    assert signer.verify(f"{payload}.{b64(b'0' * 32)}", now_ms=NOW) is None  # wrong signature
    assert SessionSigner(b"other key").verify(session, now_ms=NOW) is None  # other secret
    for junk in ["", "abc", "a.b.c", "!!!.???", payload, f"{payload}.", "x" * 600]:
        assert signer.verify(junk, now_ms=NOW) is None


def test_signed_but_malformed_claims_are_rejected() -> None:
    signer = SessionSigner(b"k" * 32)

    def signed(claims: object) -> str:
        raw = json.dumps(claims).encode()
        return f"{b64(raw)}.{b64(signer._sign(raw))}"

    assert signer.verify(signed({"user_id": "u-ana", "exp": NOW + 1}), now_ms=NOW) == "u-ana"
    for claims in (
        ["u-ana"],
        {"user_id": "u-ana"},
        {"user_id": "../etc", "exp": NOW + 1},
        {"user_id": 7, "exp": NOW + 1},
        {"user_id": "u-ana", "exp": "never"},
    ):
        assert signer.verify(signed(claims), now_ms=NOW) is None


def test_unset_secret_gets_a_random_key_and_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        first, second = SessionSigner.from_setting(None), SessionSigner.from_setting(None)
        configured = SessionSigner.from_setting(SecretStr("a-long-enough-session-secret"))

    assert "SESSION_SECRET is not set" in caplog.text
    assert "a-long-enough-session-secret" not in caplog.text
    _, session, _ = first.issue()
    assert first.verify(session) and second.verify(session) is None
    assert configured.verify(configured.issue("u-ana")[1]) == "u-ana"


def test_post_session_issues_a_server_chosen_user(client: TestClient, spans) -> None:
    response = client.post("/api/session", json={"name": "Ana", "user_id": "u-i-want-this"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"user_id", "session", "expires_at"}
    assert uuid.UUID(body["user_id"]).version == 4
    assert client.app.state.signer.verify(body["session"]) == body["user_id"]
    assert "session.create" in [s.name for s in spans.get_finished_spans()]


@pytest.mark.parametrize("body", [{}, {"name": 5}, {"name": "x" * 81}])
def test_post_session_validates_the_name(client: TestClient, body: dict) -> None:
    assert client.post("/api/session", json=body).status_code == 422


def test_post_session_is_rate_limited_per_client(make_settings) -> None:
    with TestClient(create_app(make_settings(rate_limit_per_minute=3))) as client:
        codes = [client.post("/api/session", json={"name": "Ana"}).status_code for _ in range(4)]
        blocked = client.post("/api/session", json={"name": "Ana"})

    assert codes == [200, 200, 200, 429]
    assert "Too many requests" in blocked.json()["detail"]
    assert 1 <= int(blocked.headers["retry-after"]) <= 60


def test_rate_limiter_is_a_sliding_window_per_key() -> None:
    limiter = RateLimiter(limit=2, window_s=60)

    assert [limiter.hit("a", 0.0), limiter.hit("a", 10.0)] == [0.0, 0.0]
    assert limiter.hit("a", 20.0) == 40.0  # the first hit leaves the window at t=60
    assert limiter.hit("b", 20.0) == 0.0  # other keys are unaffected
    assert limiter.hit("a", 60.0) == 0.0
    assert limiter.hit("a", 61.0) == 9.0


def test_rate_limiter_forgets_idle_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("confpilot.ratelimit.SWEEP_AT_KEYS", 3)
    limiter = RateLimiter(limit=5, window_s=60)
    for key in "abc":
        limiter.hit(key, 0.0)

    limiter.hit("d", 100.0)

    assert set(limiter._hits) == {"d"}
