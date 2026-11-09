"""ElasticStore: the API's Store, answered by the confpilot_es package.

A fake EsStore stands in for Elasticsearch, so these run offline. The live behaviour of the
queries themselves is covered by es/tests.
"""

from collections.abc import Callable
from typing import Any

import pytest
from confpilot_es import models as es_models
from fastapi.testclient import TestClient

from confpilot.app import create_app
from confpilot.models import KnowledgePatch, RoomSession, SearchHit, Speaker, Utterance
from confpilot.settings import Settings
from confpilot.store import MemoryStore, Store
from confpilot.store_es import ElasticStore, store_from_settings

pytestmark = pytest.mark.anyio

ANA = Speaker(user_id="u-ana", name="Ana")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeEsStore:
    """Records every call and answers with confpilot_es models, as the real EsStore does."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.closed = False
        self.session: es_models.RoomSession | None = None

    async def index_utterance(self, **kwargs: Any) -> None:
        self.calls.append(("index_utterance", kwargs))

    async def term_counts(self, room: str) -> dict[str, int]:
        self.calls.append(("term_counts", {"room": room}))
        return {"rag": 2, "sre": 1}

    async def search(self, q: str, room: str, size: int) -> list[es_models.SearchHit]:
        self.calls.append(("search", {"q": q, "room": room, "size": size}))
        return [
            es_models.SearchHit(
                utterance_id="utt-1",
                speaker=es_models.Speaker(user_id="u-ana", name="Ana"),
                spoken_at=1000,
                text="we use RAG",
                highlight="we use <mark>RAG</mark>",
                term_ids=["rag"],
            )
        ]

    async def get_knowledge(self, user_id: str) -> list[es_models.Knowledge]:
        self.calls.append(("get_knowledge", {"user_id": user_id}))
        return [es_models.Knowledge(user_id=user_id, term_id="rag", status="known")]

    async def put_knowledge(
        self, user_id: str, term_id: str, patch: dict[str, Any]
    ) -> es_models.Knowledge:
        self.calls.append(
            ("put_knowledge", {"user_id": user_id, "term_id": term_id, "patch": patch})
        )
        return es_models.Knowledge(user_id=user_id, term_id=term_id, **patch)

    async def touch_session(
        self, room: str, speaker: dict[str, Any] | None, at: int
    ) -> es_models.RoomSession:
        self.calls.append(("touch_session", {"room": room, "speaker": speaker, "at": at}))
        speakers = [es_models.Speaker(**speaker)] if speaker else []
        return es_models.RoomSession(room=room, started_at=at, last_at=at, speakers=speakers)

    async def get_session(self, room: str) -> es_models.RoomSession | None:
        self.calls.append(("get_session", {"room": room}))
        return self.session

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake() -> FakeEsStore:
    return FakeEsStore()


@pytest.fixture
def store(fake: FakeEsStore) -> ElasticStore:
    return ElasticStore(fake)  # type: ignore[arg-type]


def test_elastic_store_satisfies_the_protocol(store: ElasticStore) -> None:
    typed: Store = store
    assert typed is store


async def test_add_utterance_indexes_it_under_the_room_session(
    store: ElasticStore, fake: FakeEsStore
) -> None:
    await store.add_utterance(
        Utterance(
            utterance_id="utt-1",
            room="slc1",
            speaker=ANA,
            spoken_at=1000,
            text="we use RAG",
            term_ids=["rag"],
        )
    )
    assert fake.calls == [
        (
            "index_utterance",
            {
                "utterance_id": "utt-1",
                "room": "slc1",
                "speaker": {"user_id": "u-ana", "name": "Ana"},
                "spoken_at": 1000,
                "text": "we use RAG",
                "term_ids": ["rag"],
                "session_id": "slc1",
            },
        )
    ]


async def test_search_passes_limit_as_size_and_returns_api_hits(
    store: ElasticStore, fake: FakeEsStore
) -> None:
    hits = await store.search("what is rag", room="slc1", limit=7)
    assert fake.calls == [("search", {"q": "what is rag", "room": "slc1", "size": 7})]
    assert hits == [
        SearchHit(
            utterance_id="utt-1",
            speaker=ANA,
            spoken_at=1000,
            text="we use RAG",
            highlight="we use <mark>RAG</mark>",
            term_ids=["rag"],
        )
    ]


async def test_term_counts_pass_through(store: ElasticStore) -> None:
    assert await store.term_counts("slc1") == {"rag": 2, "sre": 1}


async def test_get_knowledge_returns_api_models(store: ElasticStore) -> None:
    [item] = await store.get_knowledge("u-ana")
    assert (item.user_id, item.term_id, item.status) == ("u-ana", "rag", "known")


async def test_put_knowledge_sends_only_the_fields_that_were_set(
    store: ElasticStore, fake: FakeEsStore
) -> None:
    result = await store.put_knowledge("u-ana", "rag", KnowledgePatch(status="learning", reps=1))
    assert fake.calls[-1][1]["patch"] == {"status": "learning", "reps": 1}
    assert (result.status, result.reps) == ("learning", 1)


async def test_put_knowledge_can_clear_due_at(store: ElasticStore, fake: FakeEsStore) -> None:
    await store.put_knowledge("u-ana", "rag", KnowledgePatch(due_at=None))
    assert fake.calls[-1][1]["patch"] == {"due_at": None}


async def test_touch_session_records_the_speaker(store: ElasticStore, fake: FakeEsStore) -> None:
    session = await store.touch_session("slc1", ANA, 1000)
    assert fake.calls[-1] == (
        "touch_session",
        {"room": "slc1", "speaker": {"user_id": "u-ana", "name": "Ana"}, "at": 1000},
    )
    assert session == RoomSession(room="slc1", started_at=1000, last_at=1000, speakers=[ANA])


async def test_touch_session_without_a_speaker(store: ElasticStore, fake: FakeEsStore) -> None:
    session = await store.touch_session("slc1", None, 5)
    assert fake.calls[-1][1]["speaker"] is None
    assert session.speakers == []


async def test_get_session_missing_and_present(store: ElasticStore, fake: FakeEsStore) -> None:
    assert await store.get_session("slc1") is None
    fake.session = es_models.RoomSession(room="slc1", started_at=1, last_at=2)
    assert await store.get_session("slc1") == RoomSession(room="slc1", started_at=1, last_at=2)


async def test_close_closes_the_client(store: ElasticStore, fake: FakeEsStore) -> None:
    await store.close()
    assert fake.closed


# ---------- choosing the store from settings ----------


def test_no_es_url_means_the_memory_store(make_settings: Callable[..., Settings]) -> None:
    assert isinstance(store_from_settings(make_settings()), MemoryStore)


def test_es_url_and_key_select_elasticsearch(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings(
        es_url="https://es.example.test:443", es_api_key="k", es_index_prefix="test-"
    )
    store = store_from_settings(settings)
    assert isinstance(store, ElasticStore)
    assert store.es.prefix == "test-"


def test_es_url_without_a_key_fails_at_startup(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValueError, match="ES_API_KEY"):
        store_from_settings(make_settings(es_url="https://es.example.test:443"))


def test_the_app_closes_the_store_on_shutdown(
    make_settings: Callable[..., Settings], fake: FakeEsStore
) -> None:
    app = create_app(make_settings(), store=ElasticStore(fake))  # type: ignore[arg-type]
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
    assert fake.closed


async def test_percolate_delegates_to_the_es_store() -> None:
    from confpilot.store_es import ElasticStore

    class FakeEs:
        async def percolate(self, text: str) -> list[str]:
            return ["rag"] if "RAG" in text else []

    store = ElasticStore(FakeEs())  # type: ignore[arg-type]
    assert await store.percolate("we use RAG") == ["rag"]
