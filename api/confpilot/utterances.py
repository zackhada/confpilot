"""What happens to a final transcript after it has been relayed: de-duplicate, match, store.

The duplicate rule is contracts/README.md section 5. It is decided by server arrival order
only, and nothing already stored is ever deleted or replaced, so no value a client sends
(such as ``started_at``) can remove another speaker's words.
"""

from collections import Counter, deque
from collections.abc import Sequence

from confpilot.matching import Matcher, normalize
from confpilot.models import TranscriptEvent, Utterance
from confpilot.store import Store
from confpilot.telemetry import tracer

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


async def store_final(store: Store, matcher: Matcher, room: str, event: TranscriptEvent) -> None:
    """Run the matcher and save the utterance with its term ids. ``event.speaker`` is set."""
    if event.speaker is None:
        raise ValueError("store_final needs the relayed event, with the speaker set")
    matches = matcher.match(transcript_words(event))
    term_ids = list(dict.fromkeys(match.term_id for match in matches))
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
