"""Knowledge upserts and the recap join against a stub client."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from confpilot_es import EsStore
from confpilot_es.knowledge import recap_body

from .stubs import StubClient

PREREQS = {"embedding": ["vector"], "vector": [], "rrf": ["hybrid-search"], "bm25": ["keyword-search"]}
HEARD = [("embedding", 3), ("rrf", 2), ("vector", 2), ("bm25", 1)]


def make_store(known: list[str]) -> tuple[EsStore, StubClient]:
    def search(index: str, **_: Any) -> dict[str, Any]:
        if index.endswith("utterances"):
            buckets = [{"key": term_id, "doc_count": count} for term_id, count in HEARD]
            return {"aggregations": {"heard": {"buckets": buckets}}}
        sources = [{"user_id": "u", "term_id": term_id, "status": "known"} for term_id in known]
        return {"hits": {"hits": [{"_source": source} for source in sources]}}

    def mget(ids: list[str], **_: Any) -> dict[str, Any]:
        return {"docs": [{"_id": i, "found": True, "_source": {"prereqs": PREREQS[i]}} for i in ids]}

    client = StubClient(search=search, mget=mget)
    return EsStore(client, prefix="confpilot-test-stub-"), client  # type: ignore[arg-type]


def test_recap_body_is_a_terms_aggregation_over_one_room() -> None:
    body = recap_body("slc1")
    assert body["query"] == {"term": {"room": "slc1"}} and body["size"] == 0
    assert body["aggs"]["heard"]["terms"]["field"] == "term_ids"


async def test_recap_for_a_newcomer_offers_only_terms_without_prerequisites() -> None:
    store, _ = make_store(known=[])
    recap = await store.recap("slc1", "u")
    assert [(item.term_id, item.count) for item in recap.heard] == HEARD
    assert recap.new_term_count == 4
    assert recap.learn_next == ["vector"]


async def test_recap_ranks_the_frontier_by_heard_count() -> None:
    store, _ = make_store(known=["vector", "keyword-search"])
    recap = await store.recap("slc1", "u")
    assert recap.new_term_count == 3
    assert recap.learn_next == ["embedding", "bm25"]  # rrf waits for hybrid-search
    assert (await store.recap("slc1", "u", learn_next_limit=1)).learn_next == ["embedding"]


async def test_put_knowledge_upserts_one_document_per_user_and_term() -> None:
    saved = {"user_id": "u", "term_id": "rrf", "status": "learning", "source": "tap", "due_at": None}
    client = StubClient(update={"get": {"_source": saved}})
    store = EsStore(client, prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    knowledge = await store.put_knowledge("u", "rrf", {"status": "learning", "due_at": None})
    call = client.calls_to("update")[0]
    assert (call["index"], call["id"]) == ("confpilot-test-stub-user-knowledge", "u:rrf")
    assert call["doc"] == {"status": "learning", "due_at": None}  # only what the patch set
    assert call["upsert"]["ease"] == 2.5 and call["upsert"]["status"] == "learning"
    assert (knowledge.status, knowledge.ease, knowledge.learned) == ("learning", 2.5, False)


async def test_put_knowledge_rejects_fields_outside_the_contract() -> None:
    store = EsStore(StubClient(), prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        await store.put_knowledge("u", "rrf", {"user_id": "someone-else"})
    with pytest.raises(ValidationError):
        await store.put_knowledge("u", "rrf", {"status": "mastered"})
