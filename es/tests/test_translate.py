"""translate_defs: batching, saving and one small live call that skips when no LLM key is set."""

from __future__ import annotations

import json

import httpx
import pytest

from confpilot_es import ConfigError, EsStore, Term
from confpilot_es.config import load_llm_config
from confpilot_es.translate import TranslateMixin

from .stubs import StubClient
from .test_llm import CONFIG, chat


class TranslatingStore(EsStore, TranslateMixin):
    """Translation is not part of `EsStore` yet; compose it here."""


def make_terms(count: int) -> list[Term]:
    fields = {"aliases": [], "category": "data", "level": 4, "prereqs": [], "source": "seed"}
    return [Term(id=f"t{n}", term=f"T{n}", simple_def=f"Definition {n}.", **fields) for n in range(count)]


def translate_store(*replies: str) -> tuple[TranslatingStore, list[httpx.Request], StubClient]:
    queue = [chat(reply) for reply in replies]
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return queue.pop(0)

    client = StubClient(bulk={"errors": False, "items": []})
    store = TranslatingStore(client, prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    store.llm_config = CONFIG
    store.llm_transport = httpx.MockTransport(handler)
    return store, requests, client


async def test_translate_defs_sends_twenty_terms_per_request_and_saves_the_lines() -> None:
    first = json.dumps({**{f"t{n}": f"linea {n}" for n in range(20)}, "other": "x"})
    store, requests, client = translate_store(first, '{"t20": "linea 20"}')
    translations = await store.translate_defs(make_terms(21), "es")
    assert len(requests) == 2
    assert "Spanish" in json.loads(requests[0].content)["messages"][0]["content"]
    assert translations == {f"t{n}": f"linea {n}" for n in range(21)}  # the unrequested id is dropped
    operations = client.calls_to("bulk")[0]["operations"]
    assert len(operations) == 42
    assert operations[:2] == [
        {"update": {"_index": "confpilot-test-stub-terms", "_id": "t0"}},
        {"doc": {"translations": {"es": "linea 0"}}},
    ]


async def test_translate_defs_can_skip_saving_and_rejects_unknown_languages() -> None:
    store, _, client = translate_store('{"t0": "linha"}')
    assert await store.translate_defs(make_terms(1), "pt", save=False) == {"t0": "linha"}
    assert client.calls == []
    with pytest.raises(ValueError, match="Unsupported language"):
        await store.translate_defs(make_terms(1), "fr")  # type: ignore[arg-type]


@pytest.mark.live
async def test_translate_defs_live() -> None:
    try:
        load_llm_config()
    except ConfigError as exc:
        pytest.skip(f"live LLM not configured: {exc}")
    store = TranslatingStore(StubClient(), prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    terms = make_terms(2)
    translated = await store.translate_defs(terms, "es", save=False)
    assert set(translated) == {term.id for term in terms}
