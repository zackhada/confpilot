"""Index lifecycle and glossary loading against a stub client: request shapes and error handling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from confpilot_es import EsStore, EsStoreError, Glossary
from confpilot_es.queries import percolator_query, term_doc

from .stubs import StubClient

REPO = Path(__file__).resolve().parents[2]
SAMPLE = Glossary.model_validate_json((REPO / "contracts/fixtures/glossary.sample.json").read_text("utf-8"))
REAL = Glossary.model_validate_json((REPO / "content/glossary.json").read_text("utf-8"))
PREFIX = "confpilot-test-stub-"


def make_store(**responses: object) -> tuple[EsStore, StubClient]:
    client = StubClient(**responses)  # type: ignore[arg-type]
    return EsStore(client, prefix=PREFIX), client  # type: ignore[arg-type]


def test_every_real_term_gets_a_query_and_an_embedded_text() -> None:
    assert all(percolator_query(term) != {"match_none": {}} for term in REAL.terms)
    docs = [term_doc(term) for term in REAL.terms]
    assert all(doc["semantic_text"].startswith(f"{doc['term']}: ") for doc in docs)
    assert all("say" not in doc or doc["say"] for doc in docs)  # nulls are left out of the index


async def test_ensure_indices_creates_only_what_is_missing() -> None:
    store, client = make_store(exists=lambda index: index.endswith("sessions"))
    created = await store.ensure_indices()
    assert created == [f"{PREFIX}{name}" for name in ("terms", "term-queries", "utterances", "user-knowledge")]
    percolator = next(call for call in client.calls_to("create") if call["index"].endswith("term-queries"))
    assert percolator["mappings"]["properties"]["query"] == {"type": "percolator"}
    assert "confpilot_fold" in percolator["settings"]["analysis"]["analyzer"]
    assert not client.calls_to("delete")  # nothing is dropped unless recreate is asked for


async def test_recreate_drops_each_index_first() -> None:
    store, client = make_store(exists=False)
    assert len(await store.ensure_indices(recreate=True)) == 5
    assert len(client.calls_to("delete")) == 5


async def test_upsert_terms_indexes_each_term_and_its_percolator_query() -> None:
    store, client = make_store(bulk={"errors": False, "items": []})
    assert await store.upsert_terms(SAMPLE.terms, version=SAMPLE.version) == len(SAMPLE.terms)
    operations = client.calls_to("bulk")[0]["operations"]
    first = SAMPLE.terms[0]
    assert len(operations) == 4 * len(SAMPLE.terms)
    assert operations[0] == {"index": {"_index": f"{PREFIX}terms", "_id": first.id}}
    assert operations[1] == term_doc(first)
    assert operations[2] == {"index": {"_index": f"{PREFIX}term-queries", "_id": first.id}}
    assert operations[3]["query"] == percolator_query(first)
    assert client.calls_to("put_mapping")[0]["meta"] == {"glossary_version": SAMPLE.version}


async def test_bulk_failures_are_surfaced() -> None:
    failed = {"errors": True, "items": [{"index": {"_index": "i", "_id": "rrf", "error": {"reason": "boom"}}}]}
    store, _ = make_store(bulk=failed)
    with pytest.raises(EsStoreError, match="rrf: boom"):
        await store.upsert_terms(SAMPLE.terms[:1])


async def test_prune_only_removes_seed_terms_that_left_the_glossary() -> None:
    store, client = make_store(delete_by_query={"deleted": 2})
    assert await store.prune_seed_terms(["rrf", "bm25"]) == 2
    calls = client.calls_to("delete_by_query")
    assert [call["index"] for call in calls] == [f"{PREFIX}terms", f"{PREFIX}term-queries"]
    assert calls[0]["query"]["bool"]["filter"] == [{"term": {"source": "seed"}}]  # LLM-added terms stay
    assert calls[0]["query"]["bool"]["must_not"] == [{"ids": {"values": ["rrf", "bm25"]}}]


async def test_get_glossary_reads_terms_and_the_stored_version() -> None:
    hits = [{"_source": json.loads(term.model_dump_json(exclude_none=True))} for term in SAMPLE.terms[:2]]
    mapping = {f"{PREFIX}terms": {"mappings": {"_meta": {"glossary_version": "sample-2"}}}}
    client = StubClient(search={"hits": {"hits": hits}})
    client.responses["get_mapping"] = type("Response", (), {"body": mapping})()  # type: ignore[assignment]
    glossary = await EsStore(client, prefix=PREFIX).get_glossary()  # type: ignore[arg-type]
    assert glossary.version == "sample-2" and glossary.terms == SAMPLE.terms[:2]
    assert client.calls_to("search")[0]["source_excludes"] == ["semantic_text"]
