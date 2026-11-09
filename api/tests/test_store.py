import pytest

from confpilot.models import (
    KnowledgePatch,
    Speaker,
    Utterance,
)
from confpilot.store import MemoryStore, Store, highlight

pytestmark = pytest.mark.anyio

ANA = Speaker(user_id="u-ana", name="Ana")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def utterance(
    uid: str, text: str, term_ids: list[str], room: str = "slc1", at: int = 1000
) -> Utterance:
    return Utterance(
        utterance_id=uid, room=room, speaker=ANA, spoken_at=at, text=text, term_ids=term_ids
    )


def test_memory_store_satisfies_the_protocol() -> None:
    store: Store = MemoryStore()
    assert store is not None


async def test_term_counts_are_per_room_and_resaving_replaces() -> None:
    store = MemoryStore()
    await store.add_utterance(utterance("a", "rag and rag", ["rag", "rag"]))
    await store.add_utterance(utterance("b", "rag with bm25", ["rag", "bm25"]))
    await store.add_utterance(utterance("b", "rag with bm25", ["rag", "bm25"]))
    await store.add_utterance(utterance("c", "pods", ["pod"], room="other"))

    assert await store.term_counts("slc1") == {"rag": 2, "bm25": 1}
    assert await store.term_counts("empty") == {}


async def test_search_is_case_insensitive_escaped_and_ranked() -> None:
    store = MemoryStore()
    await store.add_utterance(utterance("a", "We use <b>RAG</b> & BM25", ["rag", "bm25"], at=1))
    await store.add_utterance(utterance("b", "rag is common", ["rag"], at=2))
    await store.add_utterance(utterance("c", "dragging files", [], at=3))
    await store.add_utterance(utterance("d", "rag elsewhere", ["rag"], room="other", at=4))

    hits = await store.search("rag bm25", room="slc1")

    assert [h.utterance_id for h in hits] == ["a", "b"]
    assert hits[0].highlight == "We use &lt;b&gt;<mark>RAG</mark>&lt;/b&gt; &amp; <mark>BM25</mark>"
    assert hits[0].text == "We use <b>RAG</b> & BM25"
    assert [h.utterance_id for h in await store.search("RAG", room="slc1")] == ["b", "a"]
    assert [h.utterance_id for h in await store.search("RAG", room="other")] == ["d"]
    assert await store.search("  ?? ", room="slc1") == []
    assert len(await store.search("rag", room="slc1", limit=1)) == 1


async def test_one_speaker_cannot_overwrite_another_speakers_utterance() -> None:
    store = MemoryStore()
    ben = Speaker(user_id="u-ben", name="Ben")
    mine = utterance("same-id", "we use rag", ["rag"])
    theirs = mine.model_copy(update={"speaker": ben, "text": "overwritten", "term_ids": []})

    await store.add_utterance(mine)
    await store.add_utterance(theirs)

    hits = await store.search("rag", room="slc1")
    assert [(h.speaker.user_id, h.text) for h in hits] == [("u-ana", "we use rag")]
    assert await store.term_counts("slc1") == {"rag": 1}


def test_highlight_escapes_a_script_tag() -> None:
    marked, found = highlight("<script>alert('rag')</script>", frozenset({"rag"}))

    assert "<script" not in marked
    assert "<mark>rag</mark>" in marked
    assert found == 1


async def test_put_knowledge_creates_then_merges() -> None:
    store = MemoryStore()

    created = await store.put_knowledge("u-ana", "rag", KnowledgePatch(status="learning"))
    updated = await store.put_knowledge("u-ana", "rag", KnowledgePatch(interval_days=8, reps=3))

    assert (created.status, created.ease, created.learned, created.due_at) == (
        "learning",
        2.5,
        False,
        None,
    )
    assert (updated.status, updated.reps, updated.learned) == ("learning", 3, True)
    assert await store.get_knowledge("u-ana") == [updated]
    assert await store.get_knowledge("nobody") == []


async def test_sessions_track_activity_and_speakers() -> None:
    store = MemoryStore()

    assert await store.get_session("slc1") is None
    await store.touch_session("slc1", ANA, 1000)
    await store.touch_session("slc1", ANA, 3000)
    session = await store.touch_session("slc1", None, 2000)

    assert (session.started_at, session.last_at, session.speakers) == (1000, 3000, [ANA])
