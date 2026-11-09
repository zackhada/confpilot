"""Hybrid search and utterance indexing against a stub client."""

from __future__ import annotations

from confpilot_es import EsStore
from confpilot_es.search import MAX_SEARCH_SIZE, hybrid_search_body

from .stubs import StubClient

SPEAKER = {"user_id": "user-zack", "name": "Zack"}


def make_store(**responses: object) -> tuple[EsStore, StubClient]:
    client = StubClient(**responses)  # type: ignore[arg-type]
    return EsStore(client, prefix="confpilot-test-stub-"), client  # type: ignore[arg-type]


def hit(text: str, highlight: str | None = None) -> dict:
    source = {"utterance_id": "u1", "speaker": SPEAKER, "spoken_at": 1_794_000_000_000, "text": text}
    return {"_source": source, **({"highlight": {"text": [highlight]}} if highlight else {})}


def test_hybrid_body_fuses_bm25_and_semantic_with_rrf_inside_one_room() -> None:
    body = hybrid_search_body("how are results ranked?", "slc1", 5)
    rrf = body["retriever"]["rrf"]
    lexical, semantic = (retriever["standard"]["query"] for retriever in rrf["retrievers"])
    assert lexical["multi_match"]["fields"] == ["text^2", "speaker.name"]
    assert semantic == {"semantic": {"field": "semantic_text", "query": "how are results ranked?"}}
    assert rrf["filter"] == {"term": {"room": "slc1"}}
    assert body["size"] == 5 and rrf["rank_window_size"] >= 5
    highlight = body["highlight"]
    assert (highlight["encoder"], highlight["pre_tags"], highlight["post_tags"]) == ("html", ["<mark>"], ["</mark>"])


async def test_search_maps_hits_and_escapes_text_that_has_no_keyword_highlight() -> None:
    hits = [hit("RRF ranks <b>results</b>", "<mark>RRF</mark> ranks &lt;b&gt;results&lt;&#x2F;b&gt;"), hit("a & b")]
    store, client = make_store(search={"took": 5, "hits": {"hits": hits}})
    found = await store.search("RRF", "slc1", size=500)
    assert found[0].highlight.startswith("<mark>RRF</mark>")
    assert found[1].highlight == "a &amp; b"  # semantic-only hit: escaped, no marks
    assert found[0].speaker.name == "Zack" and found[0].term_ids == []
    call = client.calls_to("search")[0]
    assert call["index"] == "confpilot-test-stub-utterances" and call["size"] == MAX_SEARCH_SIZE
    assert call["search_type"] == "dfs_query_then_fetch"  # index-wide BM25 statistics


async def test_blank_question_never_reaches_elasticsearch() -> None:
    store, client = make_store()
    assert await store.search("  ", "slc1") == []
    assert client.calls == []


async def test_index_utterance_writes_the_contract_fields() -> None:
    store, client = make_store()
    await store.index_utterance("u1", "slc1", SPEAKER, 1_794_000_000_000, "we use RRF", ["rrf"], 412.0)
    call = client.calls_to("index")[0]
    assert (call["index"], call["id"], call["refresh"]) == ("confpilot-test-stub-utterances", "u1", False)
    assert call["document"] == {
        "utterance_id": "u1",
        "room": "slc1",
        "session_id": None,
        "speaker": SPEAKER,
        "spoken_at": 1_794_000_000_000,
        "text": "we use RRF",
        "term_ids": ["rrf"],
        "word_to_card_ms": 412.0,
    }
