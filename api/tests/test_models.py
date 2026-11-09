import pytest
from pydantic import ValidationError

from confpilot.models import TimePing, TranscriptEvent, client_event_adapter


def test_client_events_are_validated_by_type() -> None:
    assert isinstance(
        client_event_adapter.validate_python({"type": "time.ping", "t0": 1.5}), TimePing
    )
    transcript = client_event_adapter.validate_python(
        {
            "type": "transcript",
            "utterance_id": "3f2b-1",
            "seq": 2,
            "is_final": True,
            "text": "we use rag",
            "words": [{"w": "we", "start_ms": 0, "end_ms": 120.4}],
            "started_at": 1731177600000.6,
        }
    )
    assert isinstance(transcript, TranscriptEvent)
    assert transcript.started_at == 1731177600001


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "nope"},
        {"t0": 1},
        {"type": "knowledge.set", "term_id": "../etc", "status": "known"},
        {"type": "knowledge.set", "term_id": "rag", "status": "mastered"},
        {"type": "card.shown", "card_id": "c1"},
    ],
)
def test_bad_client_events_are_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError):
        client_event_adapter.validate_python(payload)
