"""Room sessions: one scripted upsert per touch, checked against a stub and the live project."""

from __future__ import annotations

import uuid

import pytest

from confpilot_es import EsStore, RoomSession

from .stubs import StubClient

ZACK = {"user_id": "user-zack", "name": "Zack"}
CLAYTON = {"user_id": "user-clayton", "name": "Clayton"}


async def test_touch_session_is_one_scripted_upsert_keyed_by_room() -> None:
    saved = {"room": "slc1", "started_at": 1000, "last_at": 1000, "speakers": [ZACK]}
    client = StubClient(update={"get": {"_source": saved}})
    store = EsStore(client, prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    session = await store.touch_session("slc1", ZACK, 1000)
    assert session == RoomSession(room="slc1", started_at=1000, last_at=1000, speakers=[ZACK])
    call = client.calls_to("update")[0]
    assert (call["index"], call["id"]) == ("confpilot-test-stub-sessions", "slc1")
    assert call["script"]["params"] == {"at": 1000, "speaker": ZACK}
    assert call["upsert"]["speakers"] == [ZACK] and call["upsert"]["started_at"] == 1000


async def test_get_session_returns_none_for_an_unknown_room() -> None:
    client = StubClient(get={"found": False})
    store = EsStore(client, prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    assert await store.get_session("nowhere") is None


@pytest.mark.live
async def test_session_round_trip_live(store: EsStore) -> None:
    room = f"room-{uuid.uuid4().hex[:6]}"
    assert await store.get_session(room) is None
    first = await store.touch_session(room, ZACK, 2000)
    assert first == RoomSession(room=room, started_at=2000, last_at=2000, speakers=[ZACK])
    await store.touch_session(room, CLAYTON, 5000)
    await store.touch_session(room, ZACK, 3000)  # an older event must not move last_at back
    await store.touch_session(room, None, 4000)  # a viewer adds no speaker
    session = await store.get_session(room)
    assert session == RoomSession(room=room, started_at=2000, last_at=5000, speakers=[ZACK, CLAYTON])
