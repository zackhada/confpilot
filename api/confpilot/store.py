"""Storage behind a small async Protocol.

``MemoryStore`` is what runs today. Elasticsearch implements the same Protocol later, so keep
every method something one Elasticsearch request can answer.
"""

import html
import re
from collections import Counter
from typing import Protocol

from confpilot.models import Knowledge, KnowledgePatch, RoomSession, SearchHit, Speaker, Utterance

MAX_UTTERANCES_PER_ROOM = 5000
_WORD = re.compile(r"\w+")


class Store(Protocol):
    async def add_utterance(self, utterance: Utterance) -> None:
        """Save a final utterance, keyed by (room, speaker user_id, utterance_id).

        The same speaker saving the same utterance_id again replaces it. Another speaker using
        that id is a different utterance, so nobody can overwrite someone else's words.
        """

    async def term_counts(self, room: str) -> dict[str, int]:
        """How many utterances in the room mention each term id."""

    async def search(self, q: str, room: str, limit: int = 20) -> list[SearchHit]:
        """Utterances in ``room`` matching ``q``, best first, with an HTML-escaped ``highlight``."""

    async def get_knowledge(self, user_id: str) -> list[Knowledge]:
        """Everything known about one user."""

    async def put_knowledge(self, user_id: str, term_id: str, patch: KnowledgePatch) -> Knowledge:
        """Create or update one record with the fields set in ``patch``. Return the result."""

    async def touch_session(self, room: str, speaker: Speaker | None, at: int) -> RoomSession:
        """Create the room's session if needed, record activity and the speaker."""

    async def get_session(self, room: str) -> RoomSession | None:
        """The room's session, or None if nothing happened there."""


def highlight(text: str, wanted: frozenset[str]) -> tuple[str, int]:
    """HTML-escape ``text`` and wrap whole words found in ``wanted`` in <mark>."""
    parts: list[str] = []
    found: set[str] = set()
    position = 0
    for match in _WORD.finditer(text):
        parts.append(html.escape(text[position : match.start()]))
        word = match.group()
        if word.casefold() in wanted:
            found.add(word.casefold())
            parts.append(f"<mark>{html.escape(word)}</mark>")
        else:
            parts.append(html.escape(word))
        position = match.end()
    parts.append(html.escape(text[position:]))
    return "".join(parts), len(found)


class MemoryStore:
    """In-process store. Fine for one replica and a demo; gone on restart."""

    def __init__(self) -> None:
        self._utterances: dict[str, dict[tuple[str, str], Utterance]] = {}
        self._knowledge: dict[str, dict[str, Knowledge]] = {}
        self._sessions: dict[str, RoomSession] = {}

    async def add_utterance(self, utterance: Utterance) -> None:
        room = self._utterances.setdefault(utterance.room, {})
        room[(utterance.speaker.user_id, utterance.utterance_id)] = utterance
        while len(room) > MAX_UTTERANCES_PER_ROOM:
            del room[next(iter(room))]

    async def term_counts(self, room: str) -> dict[str, int]:
        utterances = self._utterances.get(room, {}).values()
        return dict(Counter(term_id for u in utterances for term_id in set(u.term_ids)))

    async def search(self, q: str, room: str, limit: int = 20) -> list[SearchHit]:
        wanted = frozenset(w.casefold() for w in _WORD.findall(q))
        if not wanted:
            return []
        scored: list[tuple[int, SearchHit]] = []
        for utterance in self._utterances.get(room, {}).values():
            marked, score = highlight(utterance.text, wanted)
            if score:
                fields = utterance.model_dump(exclude={"room"})
                scored.append((score, SearchHit(**fields, highlight=marked)))
        scored.sort(key=lambda pair: (pair[0], pair[1].spoken_at), reverse=True)
        return [hit for _, hit in scored[:limit]]

    async def get_knowledge(self, user_id: str) -> list[Knowledge]:
        return list(self._knowledge.get(user_id, {}).values())

    async def put_knowledge(self, user_id: str, term_id: str, patch: KnowledgePatch) -> Knowledge:
        records = self._knowledge.setdefault(user_id, {})
        current = records.get(term_id) or Knowledge(user_id=user_id, term_id=term_id)
        sent = patch.model_dump(exclude_unset=True)
        changes = {k: v for k, v in sent.items() if v is not None or k == "due_at"}
        if "learned" not in changes and "interval_days" in changes:
            changes["learned"] = changes["interval_days"] >= 7
        updated = current.model_copy(update=changes)
        records[term_id] = updated
        return updated

    async def touch_session(self, room: str, speaker: Speaker | None, at: int) -> RoomSession:
        current = self._sessions.get(room) or RoomSession(room=room, started_at=at, last_at=at)
        speakers = current.speakers
        if speaker is not None and all(s.user_id != speaker.user_id for s in speakers):
            speakers = [*speakers, speaker]
        updated = current.model_copy(
            update={"last_at": max(at, current.last_at), "speakers": speakers}
        )
        self._sessions[room] = updated
        return updated

    async def get_session(self, room: str) -> RoomSession | None:
        return self._sessions.get(room)
