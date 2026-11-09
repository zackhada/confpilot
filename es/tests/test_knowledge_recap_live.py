"""User knowledge upserts and the recap aggregation, against the live project."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from confpilot_es import EsStore, Knowledge

from .demo_script import index_demo_script

pytestmark = pytest.mark.live


def new_user() -> str:
    return f"user-{uuid.uuid4().hex[:8]}"


async def test_put_knowledge_creates_with_sm2_defaults_then_merges(store: EsStore) -> None:
    user_id = new_user()
    created = await store.put_knowledge(user_id, "rrf", {"status": "learning", "source": "tap"})
    assert created == Knowledge(user_id=user_id, term_id="rrf", status="learning", source="tap")
    assert (created.ease, created.due_at, created.learned) == (2.5, None, False)

    patch = {"encounters": 3, "interval_days": 7, "reps": 2, "due_at": 1_794_000_600_000, "learned": True}
    updated = await store.put_knowledge(user_id, "rrf", patch)
    assert updated.status == "learning"
    assert (updated.encounters, updated.due_at, updated.learned) == (3, 1_794_000_600_000, True)

    doc = await store.client.get(index=store.index("user-knowledge"), id=f"{user_id}:rrf")
    assert doc["_source"]["term_id"] == "rrf"
    assert await store.get_knowledge(user_id) == [updated]


async def test_get_knowledge_is_per_user_and_sorted(store: EsStore) -> None:
    user_id = new_user()
    await store.put_knowledge(user_id, "vector", {"status": "known", "source": "probe"})
    await store.put_knowledge(user_id, "bm25", {"status": "unknown"})
    assert [item.term_id for item in await store.get_knowledge(user_id)] == ["bm25", "vector"]
    assert await store.get_knowledge(new_user()) == []


async def test_put_knowledge_rejects_fields_outside_the_contract(store: EsStore) -> None:
    with pytest.raises(ValidationError):
        await store.put_knowledge(new_user(), "rrf", {"user_id": "someone-else"})
    with pytest.raises(ValidationError):
        await store.put_knowledge(new_user(), "rrf", {"status": "mastered"})


async def test_recap_counts_heard_terms_and_ranks_the_frontier(store: EsStore) -> None:
    room = await index_demo_script(store)
    user_id = new_user()

    fresh = await store.recap(room, user_id)
    counts = {item.term_id: item.count for item in fresh.heard}
    assert fresh.heard[0].term_id == "embedding" and counts["embedding"] == 2
    assert counts["rrf"] == 1 and len(counts) == 13
    assert "service" not in counts  # ambiguous, never near a context word in the script
    assert fresh.new_term_count == 13
    # A newcomer's frontier is the heard terms with no prerequisites; rag, bm25 and rrf must wait.
    assert fresh.learn_next == ["ai-agent", "cluster", "elasticsearch", "keyword-search", "knowledge-base"]
    assert (await store.recap(room, user_id, learn_next_limit=1)).learn_next == ["ai-agent"]

    for term_id in ("keyword-search", "vector"):
        await store.put_knowledge(user_id, term_id, {"status": "known", "source": "tap"})
    later = await store.recap(room, user_id)
    assert later.new_term_count == fresh.new_term_count - 2
    assert later.learn_next[0] == "embedding"  # heard twice, and its only prerequisite is now known
    assert "bm25" in later.learn_next and "keyword-search" not in later.learn_next
    assert "rrf" not in later.learn_next  # hybrid-search is still unknown


async def test_recap_of_an_empty_room(store: EsStore) -> None:
    recap = await store.recap("nobody-here", new_user())
    assert (recap.new_term_count, recap.heard, recap.learn_next) == (0, [], [])
