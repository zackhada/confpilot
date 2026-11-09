"""`percolate` against a stub client: what is sent to Elasticsearch and how hits are resolved."""

from __future__ import annotations

import pytest
from elastic_transport import ConnectionError as TransportConnectionError

from confpilot_es import EsStore, EsStoreError
from confpilot_es.percolate import MAX_PERCOLATE_MATCHES, percolate_body

from .stubs import StubClient

KUBERNETES = {"term_id": "kubernetes", "phrases": ["kubernetes", "k8s"], "category": "cloud-native"}
AGENT = {"term_id": "ai-agent", "phrases": ["agent"], "category": "ai", "ambiguous": True, "context": []}


def make_store(**responses: object) -> tuple[EsStore, StubClient]:
    client = StubClient(**responses)  # type: ignore[arg-type]
    return EsStore(client, prefix="confpilot-test-stub-"), client  # type: ignore[arg-type]


def test_percolate_body_is_an_unscored_percolate_query_over_every_form() -> None:
    body = percolate_body(["a k 8 s pod", "a k8s pod"])
    percolate = body["query"]["constant_score"]["filter"]["percolate"]
    assert percolate == {"field": "query", "document": {"text": ["a k 8 s pod", "a k8s pod"]}}
    assert body["size"] == MAX_PERCOLATE_MATCHES
    assert {"term_id", "phrases", "category", "ambiguous", "context"} == set(body["_source"])


async def test_percolate_sends_every_form_and_resolves_the_hits() -> None:
    store, client = make_store(search={"took": 3, "hits": {"hits": [{"_source": KUBERNETES}, {"_source": AGENT}]}})
    # The agent hit is ambiguous with no same-category term nearby, so only kubernetes is kept.
    assert await store.percolate("the agent upgraded Kubernetes 1.30") == ["kubernetes"]
    call = client.calls_to("search")[0]
    assert call["index"] == "confpilot-test-stub-term-queries"
    document = call["query"]["constant_score"]["filter"]["percolate"]["document"]
    assert document == {"text": ["the agent upgraded kubernetes 130", "the agent upgraded kubernetes130"]}


async def test_blank_text_never_reaches_elasticsearch() -> None:
    store, client = make_store()
    assert await store.percolate(" ... ") == []
    assert client.calls == []


async def test_elasticsearch_errors_become_store_errors() -> None:
    store, _ = make_store(search=TransportConnectionError("connection refused"))
    with pytest.raises(EsStoreError, match=r"es\.percolate failed: ConnectionError"):
        await store.percolate("a pod")
