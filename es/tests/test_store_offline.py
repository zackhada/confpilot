"""Glossary loading and percolation against a stub client: request shapes and error handling."""

from __future__ import annotations

from pathlib import Path

import pytest
from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elastic_transport import ConnectionError as TransportConnectionError
from elasticsearch import ApiError

from confpilot_es import EsStore, EsStoreError
from confpilot_es.bootstrap import bootstrap, main, read_glossary
from confpilot_es.queries import percolator_query, term_doc

from .stubs import StubClient

REPO = Path(__file__).resolve().parents[2]
SAMPLE_GLOSSARY = REPO / "contracts" / "fixtures" / "glossary.sample.json"
REAL_GLOSSARY = REPO / "content" / "glossary.json"


def make_store(**responses: object) -> tuple[EsStore, StubClient]:
    client = StubClient(**responses)  # type: ignore[arg-type]
    return EsStore(client, prefix="confpilot-test-stub-"), client  # type: ignore[arg-type]


def test_real_glossary_parses_and_every_term_is_matchable() -> None:
    glossary = read_glossary(REAL_GLOSSARY)
    assert len(glossary.terms) == 200
    assert isinstance(glossary.version, str) and glossary.version
    assert all(percolator_query(term) != {"match_none": {}} for term in glossary.terms)
    assert all(term_doc(term)["semantic_text"].startswith(f"{term.term}: ") for term in glossary.terms)


async def test_bootstrap_creates_missing_indices_and_loads_terms() -> None:
    glossary = read_glossary(SAMPLE_GLOSSARY)
    store, client = make_store(
        exists=lambda index: index.endswith("sessions"),  # one index already there
        bulk={"errors": False, "items": []},
        delete_by_query={"deleted": 0},
    )
    assert await bootstrap(store, glossary) == len(glossary.terms)
    created = [call["index"] for call in client.calls_to("create")]
    assert created == [
        f"confpilot-test-stub-{name}" for name in ("terms", "term-queries", "utterances", "user-knowledge")
    ]
    operations = client.calls_to("bulk")[0]["operations"]
    assert len(operations) == 4 * len(glossary.terms)
    assert operations[0] == {"index": {"_index": "confpilot-test-stub-terms", "_id": glossary.terms[0].id}}
    assert operations[3]["query"] == percolator_query(glossary.terms[0])
    assert client.calls_to("put_mapping")[0]["meta"] == {"glossary_version": glossary.version}
    assert not client.calls_to("delete")  # nothing is dropped without --recreate


async def test_bulk_failures_are_surfaced() -> None:
    failed = {"errors": True, "items": [{"index": {"_index": "i", "_id": "rrf", "error": {"reason": "boom"}}}]}
    store, _ = make_store(bulk=failed)
    with pytest.raises(EsStoreError, match="rrf: boom"):
        await store.upsert_terms(read_glossary(SAMPLE_GLOSSARY).terms[:1])


async def test_percolate_sends_both_forms_and_resolves_hits() -> None:
    hits = [
        {"_source": {"term_id": "kubernetes", "phrases": ["kubernetes", "k8s"], "category": "cloud-native"}},
        {"_source": {"term_id": "ai-agent", "phrases": ["agent"], "category": "ai", "ambiguous": True, "context": []}},
    ]
    store, client = make_store(search={"took": 3, "hits": {"hits": hits}})
    assert await store.percolate("the agent upgraded Kubernetes 1.30") == ["kubernetes"]
    document = client.calls_to("search")[0]["query"]["constant_score"]["filter"]["percolate"]["document"]
    assert document == {"text": ["the agent upgraded kubernetes 130", "the agent upgraded kubernetes130"]}


async def test_blank_text_never_reaches_elasticsearch() -> None:
    store, client = make_store()
    assert await store.percolate(" ... ") == []
    assert client.calls == []


async def test_elasticsearch_errors_become_store_errors() -> None:
    node = NodeConfig("https", "localhost", 9200)
    meta = ApiResponseMeta(status=400, http_version="1.1", headers=HttpHeaders(), duration=0.01, node=node)
    rejected = ApiError("bad_request", meta=meta, body={"error": {"reason": "no such field"}})
    store, _ = make_store(search=[rejected, TransportConnectionError("connection refused")])
    with pytest.raises(EsStoreError, match=r"es\.percolate failed: HTTP 400: no such field"):
        await store.percolate("a pod")
    with pytest.raises(EsStoreError, match=r"es\.percolate failed: ConnectionError"):
        await store.percolate("a pod")


def test_bootstrap_cli_reports_a_missing_glossary(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    assert main(["--glossary", str(tmp_path / "nope.json")]) == 1
    assert "Bootstrap failed" in caplog.text
