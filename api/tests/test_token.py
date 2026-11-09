import json
import logging
from collections.abc import Callable
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from helpers import bearer

from confpilot.app import create_app
from confpilot.deepgram import (
    KEYTERM_TOKEN_BUDGET,
    MAX_KEYTERMS,
    MUST_CATCH,
    _estimated_tokens,
    choose_keyterms,
    listen_url,
)
from confpilot.models import Term

API_KEY = "dg-real-key-never-leaves-the-server"


def make_client(
    make_settings, handler: Callable[[httpx.Request], httpx.Response], **overrides: object
) -> TestClient:
    settings = make_settings(deepgram_api_key=API_KEY, deepgram_token_ttl_s=45, **overrides)
    client = TestClient(create_app(settings, http_transport=httpx.MockTransport(handler)))
    client.headers.update(bearer(client, "u-ana"))
    return client


def test_token_is_minted_with_the_server_key_and_a_full_ws_url(make_settings, spans) -> None:
    seen: list[httpx.Request] = []

    def deepgram(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"access_token": "tmp.jwt.token", "expires_in": 45.0})

    with make_client(make_settings, deepgram) as client:
        response = client.post("/api/token", json={"user_id": "u-ana"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert (body["provider"], body["token"], body["expires_in_s"]) == (
        "deepgram",
        "tmp.jwt.token",
        45,
    )
    assert API_KEY not in response.text

    (grant,) = seen
    assert (grant.method, str(grant.url)) == ("POST", "https://api.deepgram.com/v1/auth/grant")
    assert grant.headers["authorization"] == f"Token {API_KEY}"
    assert json.loads(grant.content) == {"ttl_seconds": 45}

    url = urlsplit(body["ws_url"])
    query = parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == "wss://api.deepgram.com/v1/listen"
    assert {k: v for k, v in query.items() if k != "keyterm"} == {
        "model": ["nova-3"],
        "encoding": ["linear16"],
        "sample_rate": ["16000"],
        "interim_results": ["true"],
        "punctuate": ["false"],
    }
    assert query["keyterm"][: len(MUST_CATCH)] == list(MUST_CATCH)
    assert "CrashLoopBackOff" in query["keyterm"]
    assert "keyterm=hybrid%20search" in body["ws_url"]
    span = next(s for s in spans.get_finished_spans() if s.name == "token.mint")
    assert span.attributes["confpilot.stt.keyterm_count"] == len(query["keyterm"])
    assert API_KEY not in json.dumps([dict(s.attributes) for s in spans.get_finished_spans()])


def granted(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"access_token": "tmp.jwt.token", "expires_in": 45})


def test_token_needs_a_session_for_the_same_user(make_settings) -> None:
    with make_client(make_settings, granted) as client:
        anonymous = client.post(
            "/api/token", json={"user_id": "u-ana"}, headers={"Authorization": ""}
        )
        someone_else = client.post("/api/token", json={"user_id": "u-ben"})

    assert (anonymous.status_code, someone_else.status_code) == (401, 403)


def test_token_is_rate_limited_per_user_and_per_client_address(make_settings) -> None:
    with make_client(make_settings, granted, rate_limit_per_minute=2) as client:
        ana = [client.post("/api/token", json={"user_id": "u-ana"}).status_code for _ in range(3)]
    with make_client(make_settings, granted, rate_limit_per_minute=2) as client:
        # Three different users behind one address: the address limit still applies.
        shared = [
            client.post("/api/token", json={"user_id": user}, headers=bearer(client, user))
            for user in ("u-1", "u-2", "u-3")
        ]

    assert ana == [200, 200, 429]
    assert [r.status_code for r in shared] == [200, 200, 429]
    assert "Too many requests" in shared[-1].json()["detail"]
    assert int(shared[-1].headers["retry-after"]) >= 1


def test_token_is_503_with_a_clear_message_when_the_key_is_unset(client: TestClient) -> None:
    client.headers.update(bearer(client, "u-ana"))
    response = client.post("/api/token", json={"user_id": "u-ana"})

    assert response.status_code == 503
    assert "DEEPGRAM_API_KEY is not set" in response.json()["detail"]


@pytest.mark.parametrize("body", [{}, {"user_id": ""}, {"user_id": "a b"}, {"user_id": "x" * 65}])
def test_token_validates_the_user_id(client: TestClient, body: dict) -> None:
    client.headers.update(bearer(client, "u-ana"))
    assert client.post("/api/token", json=body).status_code == 422


def refuse(request: httpx.Request) -> httpx.Response:
    return httpx.Response(403, json={"err_msg": f"bad key {API_KEY}"})


def unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError(f"no route, key was {API_KEY}", request=request)


def garbage(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"unexpected": True})


@pytest.mark.parametrize("handler", [refuse, unreachable, garbage])
def test_deepgram_failures_are_a_502_that_never_leaks_the_key(
    make_settings, caplog: pytest.LogCaptureFixture, handler
) -> None:
    with caplog.at_level(logging.DEBUG), make_client(make_settings, handler) as client:
        response = client.post("/api/token", json={"user_id": "u-ana"})

    assert response.status_code == 502
    assert "Deepgram" in response.json()["detail"]
    assert API_KEY not in response.text
    assert API_KEY not in caplog.text


def term(i: int, **overrides: object) -> Term:
    return Term(
        **{"id": f"t{i}", "term": f"Jargon{i:03d}", "level": 3, "simple_def": "x"} | overrides
    )


def test_keyterms_put_must_catch_first_and_stay_inside_the_limits() -> None:
    glossary = [
        term(0, term="rag", level=1),  # duplicate of a must-catch term
        term(1, term="Service", ambiguous=True),
        term(2, term="eBPF", level=4),
        *(term(i) for i in range(3, 300)),
    ]

    keyterms = choose_keyterms(glossary)

    assert keyterms[: len(MUST_CATCH) + 1] == [*MUST_CATCH, "eBPF"]
    assert len(keyterms) <= MAX_KEYTERMS
    assert sum(map(_estimated_tokens, keyterms)) <= KEYTERM_TOKEN_BUDGET
    assert "Service" not in keyterms
    assert len({k.casefold() for k in keyterms}) == len(keyterms)


def test_listen_url_encodes_spaces_as_percent_20_and_repeats_keyterm() -> None:
    url = listen_url(["BM25", "hybrid search", "C++ & more"])

    assert url.endswith("&keyterm=BM25&keyterm=hybrid%20search&keyterm=C%2B%2B%20%26%20more")
