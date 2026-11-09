"""The Store, answered by Elasticsearch through the ``confpilot_es`` package.

Selected when ``ES_URL`` is set. Each method is one Elasticsearch request (see es/README.md):
utterances get BM25 + semantic hybrid search fused with RRF, so "Ask" finds a moment by meaning
and across languages, and everything survives a restart or a second replica.

The two packages mirror the same contract with their own pydantic models, so this adapter only
converts between them.
"""

from confpilot_es import EsStore
from confpilot_es import models as es_models
from confpilot_es.config import EsConfig, create_client

from confpilot.models import Knowledge, KnowledgePatch, RoomSession, SearchHit, Speaker, Utterance
from confpilot.settings import Settings
from confpilot.store import MemoryStore, Store


class ElasticStore:
    """Implements ``confpilot.store.Store`` on top of ``confpilot_es.EsStore``."""

    def __init__(self, es: EsStore) -> None:
        self.es = es

    async def add_utterance(self, utterance: Utterance) -> None:
        # The live path does not refresh: Ask and Recap see a line within the index's refresh
        # interval, and the phone never waits on this write.
        await self.es.index_utterance(
            utterance_id=utterance.utterance_id,
            room=utterance.room,
            speaker=utterance.speaker.model_dump(),
            spoken_at=utterance.spoken_at,
            text=utterance.text,
            term_ids=utterance.term_ids,
            session_id=utterance.room,  # one session per room, as in confpilot_es.sessions
        )

    async def percolate(self, text: str) -> list[str]:
        return await self.es.percolate(text)

    async def term_counts(self, room: str) -> dict[str, int]:
        return await self.es.term_counts(room)

    async def search(self, q: str, room: str, limit: int = 20) -> list[SearchHit]:
        hits = await self.es.search(q, room=room, size=limit)
        return [SearchHit.model_validate(hit.model_dump()) for hit in hits]

    async def get_knowledge(self, user_id: str) -> list[Knowledge]:
        items = await self.es.get_knowledge(user_id)
        return [Knowledge.model_validate(item.model_dump()) for item in items]

    async def put_knowledge(self, user_id: str, term_id: str, patch: KnowledgePatch) -> Knowledge:
        # Only the fields the client set; an explicit null due_at clears the due date.
        changes = patch.model_dump(exclude_unset=True)
        saved = await self.es.put_knowledge(user_id, term_id, changes)
        return Knowledge.model_validate(saved.model_dump())

    async def touch_session(self, room: str, speaker: Speaker | None, at: int) -> RoomSession:
        who = speaker.model_dump() if speaker is not None else None
        return _session(await self.es.touch_session(room, who, at))

    async def get_session(self, room: str) -> RoomSession | None:
        found = await self.es.get_session(room)
        return _session(found) if found is not None else None

    async def close(self) -> None:
        await self.es.close()


def _session(session: es_models.RoomSession) -> RoomSession:
    return RoomSession.model_validate(session.model_dump())


def store_from_settings(settings: Settings) -> Store:
    """Elasticsearch when ``ES_URL`` is set, otherwise the in-memory store (tests, local UI work).

    Building the client does not connect, so a slow cluster never delays startup. A URL without
    a key is a deployment mistake and stops the app instead of silently losing every write.
    """
    if settings.es_url is None:
        return MemoryStore()
    if settings.es_api_key is None:
        raise ValueError("ES_URL is set but ES_API_KEY is not")
    config = EsConfig(url=settings.es_url, api_key=settings.es_api_key.get_secret_value())
    return ElasticStore(EsStore(create_client(config), prefix=settings.es_index_prefix))
