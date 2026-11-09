"""define_term and translate_defs: reply handling against a stub client, plus one live call.

The live test skips, visibly, while the project's LLM endpoints answer 403 Forbidden.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from confpilot_es import EsStore, EsStoreError, Term
from confpilot_es.llm import build_llm_term, parse_json_object, slugify

GOOD_REPLY = (
    '```json\n{"term": "eBPF", "aliases": ["extended berkeley packet filter", "EBPF"], "say": "ee-bee-pee-EFF",'
    ' "category": "cloud", "level": 4, "simple_def": "A safe way to run small programs inside the Linux kernel."}\n```'
)
LONG_REPLY = json.dumps({"term": "eBPF", "simple_def": " ".join(["word"] * 21)})


class StubInference:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def completion(self, inference_id: str, input: str) -> dict[str, Any]:
        self.prompts.append(input)
        return {"completion": [{"result": self.replies.pop(0)}]}


class StubClient:
    def __init__(self, replies: list[str]) -> None:
        self.inference = StubInference(replies)
        self.bulk_operations: list[dict[str, Any]] = []

    def options(self, **_: Any) -> StubClient:
        return self

    async def bulk(self, operations: list[dict[str, Any]], refresh: bool) -> dict[str, Any]:
        self.bulk_operations = operations
        return {"errors": False, "items": []}


def stub_store(*replies: str) -> tuple[EsStore, StubClient]:
    client = StubClient(list(replies))
    return EsStore(client, prefix="confpilot-test-stub-"), client  # type: ignore[arg-type]


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


async def test_define_term_retries_once_with_feedback() -> None:
    store, client = stub_store(LONG_REPLY, GOOD_REPLY)
    term = await store.define_term("eBPF", "We moved the proxies to eBPF.")
    assert term.simple_def == "A safe way to run small programs inside the Linux kernel."
    assert "rejected" in client.inference.prompts[1] and "rejected" not in client.inference.prompts[0]


async def test_define_term_gives_up_clearly() -> None:
    store, _ = stub_store(LONG_REPLY, "not json")
    with pytest.raises(EsStoreError, match="could not define 'eBPF'"):
        await store.define_term("eBPF", "We moved the proxies to eBPF.")


async def test_translate_defs_saves_only_requested_ids() -> None:
    terms = [
        Term(id="rrf", term="RRF", aliases=[], category="data", level=4, simple_def="d", prereqs=[], source="seed")
    ]
    store, client = stub_store('{"rrf": "Método para combinar listas.", "other": "x"}')
    assert await store.translate_defs(terms, "es") == {"rrf": "Método para combinar listas."}
    assert client.bulk_operations == [
        {"update": {"_index": "confpilot-test-stub-terms", "_id": "rrf"}},
        {"doc": {"translations": {"es": "Método para combinar listas."}}},
    ]
    with pytest.raises(ValueError, match="Unsupported language"):
        await store.translate_defs(terms, "fr")  # type: ignore[arg-type]


@pytest.mark.live
async def test_define_and_translate_live(store: EsStore) -> None:
    try:
        term = await store.define_term("eBPF", "We moved the sidecar proxies to eBPF so the mesh adds less latency.")
    except EsStoreError as exc:
        if "HTTP 403" in str(exc):
            pytest.skip(f"LLM endpoint {store.llm_endpoint} is forbidden on this project: {exc}")
        raise
    assert term.source == "llm" and len(term.simple_def.split()) <= 20
    translated = await store.translate_defs([term], "es", save=False)
    assert translated[term.id]
