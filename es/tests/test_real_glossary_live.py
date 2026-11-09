"""The real 200-term glossary on throwaway indices: it must load, and catch the demo's key terms."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from confpilot_es import EsStore
from confpilot_es.bootstrap import bootstrap, read_glossary

pytestmark = pytest.mark.live

CONTENT = Path(__file__).resolve().parents[2] / "content"
REAL_GLOSSARY = CONTENT / "glossary.json"
TALK_TRACK = CONTENT / "stt-fixtures" / "talk_track.txt"
MUST_CATCH = {"sre", "rag", "embedding", "bm25", "rrf"}


@pytest_asyncio.fixture(scope="module")
async def real_store(store: EsStore) -> AsyncIterator[EsStore]:
    real = EsStore(store.client, prefix=f"confpilot-test-{uuid.uuid4().hex[:8]}-real-", refresh=True)
    try:
        await bootstrap(real, read_glossary(REAL_GLOSSARY), recreate=True)
        yield real
    finally:
        await real.delete_indices()


async def test_real_glossary_loads_every_term(real_store: EsStore) -> None:
    expected = read_glossary(REAL_GLOSSARY)
    glossary = await real_store.get_glossary()
    assert glossary.version == expected.version
    assert {term.id for term in glossary.terms} == {term.id for term in expected.terms}
    queries = await real_store.client.count(index=real_store.index("term-queries"))
    assert queries["count"] == len(expected.terms)


async def test_talk_track_catches_the_five_must_catch_terms(real_store: EsStore) -> None:
    lines = [line for line in TALK_TRACK.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    for line in lines:
        found = await real_store.percolate(line)
        print(f"\ntalk track line matched {len(found)} terms: {found}")
        assert MUST_CATCH <= set(found), f"missed {sorted(MUST_CATCH - set(found))}"


async def test_ambiguous_real_terms_need_a_same_category_neighbour(real_store: EsStore) -> None:
    assert "ai-agent" not in await real_store.percolate("my travel agent booked the flights")
    assert "ai-agent" in await real_store.percolate("we use RAG so the agent has facts")


async def test_pruning_removes_seed_terms_that_left_the_glossary(real_store: EsStore) -> None:
    glossary = read_glossary(REAL_GLOSSARY)
    kept = [term for term in glossary.terms if term.id != "rrf"]
    assert await real_store.prune_seed_terms(term.id for term in kept) == 1
    assert "rrf" not in await real_store.percolate("and RRF to rank the results")
    assert await real_store.upsert_terms([term for term in glossary.terms if term.id == "rrf"]) == 1
    assert "rrf" in await real_store.percolate("and RRF to rank the results")
