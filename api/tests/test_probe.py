import asyncio
import json
import logging
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from helpers import bearer

from confpilot.app import create_app

LLM_KEY = "llm-key-never-leaves-the-server"
INTRO = "Hi, I'm an SRE, we run Kubernetes clusters and I want to learn about RAG"
REQUEST = {"user_id": "u-ana", "transcript": INTRO}
HEURISTIC = {
    "role": "attendee",
    "domain": "cloud-native",
    "known_term_ids": ["sre", "kubernetes", "cluster", "rag"],
    "english_level": "B1",
    "goals": [],
}


def chat_reply(content: object) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": text}}]}
    )


def make_client(make_settings, handler: Callable, **overrides: object) -> TestClient:
    settings = make_settings(
        llm_api_key=LLM_KEY,
        llm_base_url="https://llm.test/v1/",
        llm_model="test-model",
        **overrides,
    )
    client = TestClient(create_app(settings, http_transport=httpx.MockTransport(handler)))
    client.headers.update(bearer(client, "u-ana"))
    return client


@pytest.fixture(autouse=True)
def signed_in_as_ana(client: TestClient) -> None:
    client.headers.update(bearer(client, "u-ana"))


def probe_span(spans):
    return next(s for s in spans.get_finished_spans() if s.name == "probe")


def test_without_an_llm_key_the_heuristic_answers(client: TestClient, spans) -> None:
    response = client.post("/api/probe", json=REQUEST)

    assert response.status_code == 200
    assert response.json() == HEURISTIC
    assert probe_span(spans).attributes["confpilot.probe.source"] == "heuristic"


def test_heuristic_with_nothing_recognised(client: TestClient) -> None:
    body = client.post("/api/probe", json={"user_id": "u-ana", "transcript": "hello there"}).json()

    assert (body["known_term_ids"], body["domain"]) == ([], "general")


def test_llm_answer_is_used_and_cleaned(make_settings, spans) -> None:
    seen: list[httpx.Request] = []

    def llm(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return chat_reply(
            {
                "role": "Site reliability engineer",
                "domain": "Platform operations",
                "known_term_ids": ["pod", "sre", "made-up-term", "pod"],
                "english_level": "C1",
                "goals": ["learn RAG", "b", "c", "d", "e", "one too many"],
            }
        )

    with make_client(make_settings, llm) as client:
        body = client.post("/api/probe", json=REQUEST).json()

    assert body == {
        "role": "Site reliability engineer",
        "domain": "Platform operations",
        # Unknown ids and repeats are dropped. "rag" was spoken ("I want to learn about RAG")
        # but the LLM did not call it known, and the LLM is trusted over the heuristic.
        "known_term_ids": ["pod", "sre"],
        "english_level": "C1",
        "goals": ["learn RAG", "b", "c", "d", "e"],
    }
    (call,) = seen
    assert str(call.url) == "https://llm.test/v1/chat/completions"
    assert call.headers["authorization"] == f"Bearer {LLM_KEY}"
    sent = json.loads(call.content)
    assert sent["model"] == "test-model"
    assert sent["max_tokens"] == 600  # a small cap keeps the spend per call low
    assert "response_format" not in sent  # endpoints disagree on it, so the prompt asks for JSON
    assert sent["messages"][1] == {"role": "user", "content": INTRO}
    assert "rrf: RRF" in sent["messages"][0]["content"]
    assert probe_span(spans).attributes["confpilot.probe.source"] == "llm"


def test_a_reply_wrapped_in_prose_or_a_code_fence_is_still_read(make_settings) -> None:
    def fenced(request: httpx.Request) -> httpx.Response:
        return chat_reply(
            "Here you go:\n```json\n" + json.dumps(HEURISTIC | {"role": "SRE"}) + "\n```"
        )

    with make_client(make_settings, fenced) as client:
        body = client.post("/api/probe", json=REQUEST).json()

    assert body["role"] == "SRE"


def test_probe_needs_a_session_for_the_same_user_and_is_rate_limited(make_settings) -> None:
    with make_client(make_settings, not_json, rate_limit_per_minute=2) as client:
        anonymous = client.post("/api/probe", json=REQUEST, headers={"Authorization": ""})
        someone_else = client.post("/api/probe", json=REQUEST | {"user_id": "u-ben"})
        codes = [client.post("/api/probe", json=REQUEST).status_code for _ in range(3)]

    assert (anonymous.status_code, someone_else.status_code) == (401, 403)
    assert codes == [200, 200, 429]


def server_error(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text=f"boom {LLM_KEY}")


def unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("no route", request=request)


def not_json(request: httpx.Request) -> httpx.Response:
    return chat_reply("Sure! Here is the profile you asked for.")


def wrong_shape(request: httpx.Request) -> httpx.Response:
    return chat_reply({"role": "x", "domain": "y", "known_term_ids": [], "english_level": "Z9"})


def no_choices(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"choices": []})


async def too_slow(request: httpx.Request) -> httpx.Response:
    await asyncio.sleep(5)
    return chat_reply(HEURISTIC)


@pytest.mark.parametrize(
    "handler", [server_error, unreachable, not_json, wrong_shape, no_choices, too_slow]
)
def test_any_llm_failure_falls_back_to_the_heuristic(
    make_settings, spans, caplog: pytest.LogCaptureFixture, handler
) -> None:
    with caplog.at_level(logging.DEBUG):
        with make_client(make_settings, handler, probe_timeout_s=0.2) as client:
            response = client.post("/api/probe", json=REQUEST)

    assert response.status_code == 200
    assert response.json() == HEURISTIC
    attributes = probe_span(spans).attributes
    assert attributes["confpilot.probe.source"] == "heuristic"
    assert attributes["confpilot.probe.fallback_reason"]
    failure = next(e for e in probe_span(spans).events if e.name == "exception")
    assert failure.attributes["exception.type"] == attributes["confpilot.probe.fallback_reason"]
    assert LLM_KEY not in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"user_id": "u-ana"},
        {"user_id": "a b", "transcript": "x"},
        {**REQUEST, "transcript": "x" * 8001},
    ],
)
def test_probe_validates_its_input(client: TestClient, body: dict) -> None:
    assert client.post("/api/probe", json=body).status_code == 422
