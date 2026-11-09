"""Hybrid search over the demo conversation, including the multilingual claim."""

from __future__ import annotations

import statistics
import time

import pytest
import pytest_asyncio

from confpilot_es import EsStore

from .demo_script import RAG_LINE, RRF_LINE, index_demo_script

pytestmark = pytest.mark.live

LATENCY_SAMPLES = 15


@pytest_asyncio.fixture(scope="module")
async def room(store: EsStore) -> str:
    return await index_demo_script(store)


async def test_question_about_a_speaker_and_term_finds_his_line(store: EsStore, room: str) -> None:
    hits = await store.search("What did Zack say about RAG?", room, size=3)
    assert hits[0].text == RAG_LINE
    assert hits[0].speaker.name == "Zack"
    assert "<mark>RAG</mark>" in hits[0].highlight
    assert {"rag", "hybrid-search", "keyword-search", "elasticsearch"} <= set(hits[0].term_ids)


async def test_spanish_question_finds_the_english_rrf_line(store: EsStore, room: str) -> None:
    hits = await store.search("¿cómo ordena los resultados?", room, size=3)
    texts = [hit.text for hit in hits]
    print(f"\nSpanish query: RRF line at rank {texts.index(RRF_LINE) + 1 if RRF_LINE in texts else 'none'}")
    assert RRF_LINE in texts


async def test_highlight_is_html_escaped(store: EsStore, room: str) -> None:
    await store.index_utterance(
        utterance_id=f"{room}-xss",
        room=room,
        speaker={"user_id": "user-zack", "name": "Zack"},
        spoken_at=1,
        text="<script>alert('x')</script> the percolator & friends",
    )
    hits = await store.search("percolator", room, size=1)
    assert hits[0].highlight.count("<mark>") == 1
    assert "<script>" not in hits[0].highlight
    assert "&lt;script&gt;" in hits[0].highlight
    assert "<mark>percolator</mark> &amp; friends" in hits[0].highlight


async def test_search_is_scoped_to_the_room(store: EsStore, room: str) -> None:
    assert await store.search("RAG", "some-other-room") == []
    assert await store.search("   ", room) == []


async def test_search_latency(store: EsStore, room: str) -> None:
    await store.search("hybrid search", room)
    samples: list[float] = []
    for _ in range(LATENCY_SAMPLES):
        started = time.perf_counter()
        await store.search("What did Zack say about RAG?", room)
        samples.append((time.perf_counter() - started) * 1000)
    p50 = statistics.median(samples)
    p95 = statistics.quantiles(samples, n=20)[18]
    print(f"\nhybrid search latency over {LATENCY_SAMPLES} calls: p50={p50:.1f} ms p95={p95:.1f} ms")
    assert p95 < 5000
