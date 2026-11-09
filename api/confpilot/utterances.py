"""What happens to a final transcript after it has been relayed: de-duplicate, match, store.

The duplicate rule is contracts/README.md section 5. It is decided by server arrival order
only, and nothing already stored is ever deleted or replaced, so no value a client sends
(such as ``started_at``) can remove another speaker's words.
"""

import logging
from collections import Counter, deque
from collections.abc import Callable, Collection, Sequence

from opentelemetry.trace import Status, StatusCode

from confpilot.matching import Matcher, normalize
from confpilot.models import TranscriptEvent, Utterance
from confpilot.store import Store
from confpilot.telemetry import tracer

_log = logging.getLogger(__name__)

# Called with the term ids the percolator found that the phone's matcher could not have.
OnServerTerms = Callable[[list[str]], None]

DUPLICATE_WINDOW_S = 3.0  # server clock, between the two arrivals
DUPLICATE_OVERLAP = 0.8
MIN_DUPLICATE_WORDS = 4  # shorter finals ("yeah", "ok thanks") are never duplicates


def transcript_words(event: TranscriptEvent) -> list[str]:
    return [word.w for word in event.words] or event.text.split()


def is_duplicate(a: Sequence[str], b: Sequence[str]) -> bool:
    """Both have at least four normalized words, and the words in common (counting repeats)
    are at least 80% of the LONGER one's word count."""
    if min(len(a), len(b)) < MIN_DUPLICATE_WORDS:
        return False
    common = sum((Counter(a) & Counter(b)).values())
    return common >= DUPLICATE_OVERLAP * max(len(a), len(b))


class RecentFinals:
    """Both phones may hear both voices. Remember stored finals briefly to keep one copy."""

    def __init__(self) -> None:
        self._rooms: dict[str, deque[tuple[float, str, tuple[str, ...]]]] = {}

    def admit(self, room: str, user_id: str, words: Sequence[str], now: float) -> bool:
        """True if this final should be stored. False if it is empty, or if it repeats a
        final that another speaker got to the server within the last three seconds."""
        normalized = tuple(token.text for token in normalize(words))
        recent = self._rooms.get(room, deque())
        while recent and now - recent[0][0] > DUPLICATE_WINDOW_S:
            recent.popleft()
        fresh = bool(normalized) and not any(
            other != user_id and is_duplicate(normalized, other_words)
            for _, other, other_words in recent
        )
        if fresh:
            recent.append((now, user_id, normalized))
        if recent:
            self._rooms[room] = recent
        else:
            self._rooms.pop(room, None)  # quiet rooms cost nothing
        return fresh

    def forget(self, room: str, user_id: str, words: Sequence[str], at: float) -> None:
        """Undo this admission when its storage work is dropped."""
        normalized = tuple(token.text for token in normalize(words))
        recent = self._rooms.get(room)
        if recent is None:
            return
        try:
            recent.remove((at, user_id, normalized))
        except ValueError:
            pass  # already expired
        if not recent:
            self._rooms.pop(room, None)


async def store_final_or_release(
    store: Store,
    matcher: Matcher,
    recent: RecentFinals,
    room: str,
    event: TranscriptEvent,
    words: Sequence[str],
    admitted_at: float,
    known_ids: Collection[str],
    on_server_terms: OnServerTerms | None = None,
) -> None:
    """Store an admitted final. If storing fails, release its admission, so that the other
    phone's copy of the same sentence can still be stored, then let the failure be logged."""
    try:
        await store_final(store, matcher, room, event, known_ids, on_server_terms)
    except Exception:
        if event.speaker is not None:
            recent.forget(room, event.speaker.user_id, words, admitted_at)
        raise


async def percolate_extra(
    store: Store, text: str, phone_term_ids: Sequence[str], known_ids: Collection[str]
) -> list[str]:
    """Tier 2: terms the Elasticsearch percolator finds that the phone's matcher did not.

    A failing percolator costs only the tier 2 cards, never the stored utterance.
    """
    with tracer.start_as_current_span("utterance.percolate") as span:
        try:
            found = await store.percolate(text)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, "percolate failed"))
            _log.warning("percolate failed, storing without tier 2 terms", exc_info=True)
            return []
        already = set(phone_term_ids)
        extra = [
            term_id
            for term_id in dict.fromkeys(found)
            if term_id not in already and term_id in known_ids
        ]
        span.set_attribute("confpilot.percolate.found", len(found))
        span.set_attribute("confpilot.percolate.extra", len(extra))
        return extra


async def store_final(
    store: Store,
    matcher: Matcher,
    room: str,
    event: TranscriptEvent,
    known_ids: Collection[str],
    on_server_terms: OnServerTerms | None = None,
) -> None:
    """Match (phone rules, then the percolator) and save the utterance with its term ids.

    ``event.speaker`` is set. Percolator-only terms go to ``on_server_terms`` before the write,
    so their cards never wait on storage.
    """
    if event.speaker is None:
        raise ValueError("store_final needs the relayed event, with the speaker set")
    matches = matcher.match(transcript_words(event))
    term_ids = list(dict.fromkeys(match.term_id for match in matches))
    extra = await percolate_extra(store, event.text, term_ids, known_ids)
    if extra and on_server_terms is not None:
        on_server_terms(extra)
    term_ids = term_ids + extra
    attributes = {
        "confpilot.room": room,
        "confpilot.utterance.id": event.utterance_id,
        "confpilot.utterance.term_count": len(term_ids),
    }
    with tracer.start_as_current_span("utterance.store", attributes=attributes):
        utterance = Utterance(
            utterance_id=event.utterance_id,
            room=room,
            speaker=event.speaker,
            spoken_at=event.started_at,
            text=event.text,
            term_ids=term_ids,
        )
        await store.add_utterance(utterance)
        await store.touch_session(room, event.speaker, event.started_at)
