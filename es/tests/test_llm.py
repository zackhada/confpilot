"""define_term and translate_defs: request shape, retries and reply validation against a mock
HTTP transport, plus one small live call that skips when no LLM key is configured."""

from __future__ import annotations

import json

import httpx
import pytest

from confpilot_es import ConfigError, EsStore, LlmError, Term
from confpilot_es.config import LlmConfig, load_llm_config
from confpilot_es.llm import build_llm_term, parse_json_object, slugify

from .stubs import StubClient

CONFIG = LlmConfig(base_url="https://llm.test/v1", api_key="test-key", model="test-model")
GOOD_REPLY = (
    '```json\n{"term": "eBPF", "aliases": ["extended berkeley packet filter", "EBPF"], "say": "ee-bee-pee-EFF",'
    ' "category": "cloud", "level": 4, "simple_def": "A safe way to run small programs inside the Linux kernel."}\n```'
)
LONG_REPLY = json.dumps({"term": "eBPF", "simple_def": " ".join(["word"] * 21)})


def chat(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content}}]})


def llm_store(*responses: httpx.Response | Exception) -> tuple[EsStore, list[httpx.Request], StubClient]:
    queue = list(responses)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        response = queue.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    client = StubClient(bulk={"errors": False, "items": []})
    store = EsStore(client, prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    store.llm_config = CONFIG
    store.llm_transport = httpx.MockTransport(handler)
    return store, requests, client


def test_reply_parsing_and_validation() -> None:
    term = build_llm_term("ebpf", parse_json_object(GOOD_REPLY))
    assert (term.id, term.term, term.source, term.level, term.category) == ("ebpf", "eBPF", "llm", 4, "cloud")
    assert term.aliases == ["extended berkeley packet filter"]  # the term itself is not an alias
    assert slugify("Service Mesh (Istio)") == "service-mesh-istio"
    with pytest.raises(ValueError, match="21 words"):
        build_llm_term("ebpf", parse_json_object(LONG_REPLY))
    with pytest.raises(ValueError, match="define itself"):
        build_llm_term("pod", {"simple_def": "A pod is a group of containers."})
    with pytest.raises(ValueError, match="no JSON object"):
        parse_json_object("I cannot help with that.")


async def test_define_term_calls_the_chat_completions_endpoint() -> None:
    store, requests, _ = llm_store(chat(GOOD_REPLY))
    term = await store.define_term("eBPF", "We moved the proxies to eBPF.")
    assert term.simple_def == "A safe way to run small programs inside the Linux kernel."
    request = requests[0]
    body = json.loads(request.content)
    assert str(request.url) == "https://llm.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-key"
    assert body["model"] == "test-model" and 0 < body["max_tokens"] <= 500
    assert "<sentence>We moved the proxies to eBPF.</sentence>" in body["messages"][0]["content"]


async def test_define_term_asks_again_with_feedback_when_the_reply_breaks_the_rules() -> None:
    store, requests, _ = llm_store(chat(LONG_REPLY), chat(GOOD_REPLY))
    assert (await store.define_term("eBPF", "We moved the proxies to eBPF.")).source == "llm"
    prompts = [json.loads(request.content)["messages"][0]["content"] for request in requests]
    assert "rejected" in prompts[1] and "rejected" not in prompts[0]


async def test_define_term_gives_up_clearly() -> None:
    store, _, _ = llm_store(chat(LONG_REPLY), chat("not json"))
    with pytest.raises(LlmError, match="could not define 'eBPF'"):
        await store.define_term("eBPF", "We moved the proxies to eBPF.")


async def test_one_retry_on_a_server_error_or_timeout_and_none_on_a_client_error() -> None:
    store, requests, _ = llm_store(httpx.Response(503, text="overloaded"), chat(GOOD_REPLY))
    assert (await store.define_term("eBPF", "x")).id == "ebpf"
    assert len(requests) == 2

    store, requests, _ = llm_store(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"))
    with pytest.raises(LlmError, match=r"llm\.define failed: ReadTimeout"):
        await store.define_term("eBPF", "x")
    assert len(requests) == 2

    store, requests, _ = llm_store(httpx.Response(401, text="invalid x-api-key"))
    with pytest.raises(LlmError, match="HTTP 401") as raised:
        await store.define_term("eBPF", "x")
    assert len(requests) == 1 and "test-key" not in str(raised.value)


async def test_an_unexpected_response_shape_is_reported() -> None:
    store, _, _ = llm_store(httpx.Response(200, json={"choices": []}))
    with pytest.raises(LlmError, match="unexpected response shape"):
        await store.define_term("eBPF", "x")
    cut_off = {"choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": ""}}]}
    store, _, _ = llm_store(httpx.Response(200, json=cut_off))
    with pytest.raises(LlmError, match=r"empty reply \(finish_reason: length\)"):
        await store.define_term("eBPF", "x")


def test_thinking_is_switched_off_for_anthropic_only() -> None:
    anthropic = LlmConfig(base_url="https://api.anthropic.com/v1", api_key="k", model="m")
    assert anthropic.extra_body == {"thinking": {"type": "disabled"}}
    assert CONFIG.extra_body == {}


async def test_translate_defs_batches_and_saves_only_requested_ids() -> None:
    terms = [
        Term(id=f"t{n}", term=f"T{n}", aliases=[], category="data", level=4, simple_def="d", prereqs=[], source="seed")
        for n in range(21)
    ]
    first = json.dumps({**{f"t{n}": f"línea {n}" for n in range(20)}, "other": "x"})
    store, requests, client = llm_store(chat(first), chat('{"t20": "línea 20"}'))
    translations = await store.translate_defs(terms, "es")
    assert len(requests) == 2  # 20 terms per request
    assert translations == {f"t{n}": f"línea {n}" for n in range(21)}
    operations = client.calls_to("bulk")[0]["operations"]
    assert operations[:2] == [
        {"update": {"_index": "confpilot-test-stub-terms", "_id": "t0"}},
        {"doc": {"translations": {"es": "línea 0"}}},
    ]
    assert len(operations) == 42
    with pytest.raises(ValueError, match="Unsupported language"):
        await store.translate_defs(terms, "fr")  # type: ignore[arg-type]


def test_llm_config_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "ENV_FILE"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigError, match="LLM_BASE_URL, LLM_API_KEY and LLM_MODEL"):
        load_llm_config()
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.test/v1/")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "m")
    assert load_llm_config() == LlmConfig(base_url="https://llm.test/v1", api_key="k", model="m")


@pytest.mark.live
async def test_define_and_translate_live() -> None:
    try:
        load_llm_config()
    except ConfigError as exc:
        pytest.skip(f"live LLM not configured: {exc}")
    store = EsStore(StubClient(), prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    sentences = {
        "eBPF": "We moved the sidecar proxies to eBPF so the mesh adds less latency.",
        "canary deploy": "We ship every change as a canary deploy to five percent of users first.",
    }
    terms = [await store.define_term(term, sentence) for term, sentence in sentences.items()]
    for term in terms:
        assert term.source == "llm" and 0 < len(term.simple_def.split()) <= 20
        print(f"\n{term.term}: {term.simple_def}")
    translated = await store.translate_defs(terms, "es", save=False)
    assert set(translated) == {term.id for term in terms}
