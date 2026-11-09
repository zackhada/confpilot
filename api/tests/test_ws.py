import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from confpilot.app import create_app

ANA = {"user_id": "u-ana", "name": "Ana"}
BEN = {"user_id": "u-ben", "name": "Ben"}
ANA_URL = "/ws/rooms/slc1?user_id=u-ana&name=Ana&role=speaker"
BEN_URL = "/ws/rooms/slc1?user_id=u-ben&name=Ben&role=speaker"
STAGE_URL = "/ws/rooms/slc1?user_id=stage-1&name=Stage&role=viewer"
STATE_BOTH = {
    "type": "room.state",
    "members": [{**ANA, "role": "speaker"}, {**BEN, "role": "speaker"}],
}
TRANSCRIPT = {
    "type": "transcript",
    "utterance_id": "utt-1",
    "seq": 3,
    "is_final": False,
    "text": "we use rag",
    "words": [
        {"w": "we", "start_ms": 0, "end_ms": 100},
        {"w": "use", "start_ms": 110, "end_ms": 200},
        {"w": "rag", "start_ms": 210, "end_ms": 400},
    ],
    "started_at": 1731177600000,
}
CARD_SHOWN = {
    "type": "card.shown",
    "card_id": "card-1",
    "term_id": "rag",
    "tier": 1,
    "utterance_id": "utt-1",
    "spoken_at": 1731177600400,
    "rendered_at": 1731177600730,
    "word_to_card_ms": 330,
}


def ping(socket, t0: float = 1.0) -> dict:
    """Round trip. Whatever arrives next proves nothing else was queued for this socket."""
    socket.send_json({"type": "time.ping", "t0": t0})
    return socket.receive_json()


@pytest.fixture
def room(client: TestClient):
    with client.websocket_connect(ANA_URL) as ana:
        assert ana.receive_json() == {"type": "room.state", "members": [{**ANA, "role": "speaker"}]}
        with client.websocket_connect(BEN_URL) as ben:
            assert ben.receive_json() == STATE_BOTH
            assert ana.receive_json() == STATE_BOTH
            yield ana, ben


def test_leaving_broadcasts_room_state(client: TestClient) -> None:
    with client.websocket_connect(ANA_URL) as ana:
        ana.receive_json()
        with client.websocket_connect(STAGE_URL) as stage:
            stage.receive_json()
            assert ana.receive_json()["members"][1] == {
                "user_id": "stage-1",
                "name": "Stage",
                "role": "viewer",
            }
        assert ana.receive_json() == {"type": "room.state", "members": [{**ANA, "role": "speaker"}]}


def test_time_ping_gets_a_pong_in_server_time(room) -> None:
    ana, _ = room
    before = time.time() * 1000

    pong = ping(ana, t0=42.5)

    assert pong["type"] == "time.pong"
    assert pong["t0"] == 42.5
    assert before - 5 <= pong["server_ts"] <= time.time() * 1000 + 5


def test_transcript_is_relayed_to_everyone_else_with_the_speaker(room, spans) -> None:
    ana, ben = room

    ana.send_json(TRANSCRIPT)

    assert ben.receive_json() == {**TRANSCRIPT, "speaker": ANA}
    assert ping(ana)["type"] == "time.pong"  # the sender does not get its own transcript back
    relay = next(s for s in spans.get_finished_spans() if s.name == "transcript.relay")
    assert relay.attributes["confpilot.room"] == "slc1"
    assert relay.attributes["confpilot.room.recipients"] == 1


def test_a_client_cannot_forge_the_speaker(room) -> None:
    ana, ben = room

    ana.send_json({**TRANSCRIPT, "speaker": {"user_id": "u-ben", "name": "Not Ana"}})

    assert ben.receive_json()["speaker"] == ANA


def test_viewers_cannot_send_transcripts(client: TestClient, room) -> None:
    ana, _ = room
    with client.websocket_connect(STAGE_URL) as stage:
        stage.receive_json()
        ana.receive_json()

        stage.send_json(TRANSCRIPT)

        assert stage.receive_json()["code"] == "forbidden"
        assert ping(ana)["type"] == "time.pong"


def latency_points(metric_reader) -> list:
    """Points of the latency histogram. The in-memory reader is cumulative across tests."""
    data = metric_reader.get_metrics_data()
    return [
        point
        for rm in (data.resource_metrics if data else [])
        for sm in rm.scope_metrics
        for m in sm.metrics
        if m.name == "confpilot.card.word_to_card_ms"
        for point in m.data.data_points
    ]


def test_card_shown_is_relayed_and_recorded(room, spans, metric_reader) -> None:
    ana, ben = room
    before = sum(p.count for p in latency_points(metric_reader))

    ben.send_json(CARD_SHOWN)

    assert ana.receive_json() == {**CARD_SHOWN, "user": BEN}
    assert ping(ben)["type"] == "time.pong"
    push = next(s for s in spans.get_finished_spans() if s.name == "card.push")
    assert push.attributes["confpilot.card.tier"] == 1
    points = latency_points(metric_reader)
    assert sum(p.count for p in points) == before + 1
    # The room id is client-chosen, so it stays off the metric and on the span.
    assert all(dict(p.attributes) == {"confpilot.card.tier": 1} for p in points)
    assert push.attributes["confpilot.room"] == "slc1"
    assert 800 in points[0].explicit_bounds


def test_a_wild_latency_is_relayed_but_kept_out_of_the_histogram(room, metric_reader) -> None:
    ana, ben = room
    before = sum(p.count for p in latency_points(metric_reader))

    ben.send_json({**CARD_SHOWN, "word_to_card_ms": -86_400_000})

    assert ana.receive_json()["word_to_card_ms"] == -86_400_000
    assert sum(p.count for p in latency_points(metric_reader)) == before


def test_knowledge_set_updates_the_store(client: TestClient, room) -> None:
    ana, _ = room

    ana.send_json({"type": "knowledge.set", "term_id": "rag", "status": "known"})
    ping(ana)

    record = client.app.state.store._knowledge["u-ana"]["rag"]
    assert (record.status, record.source) == ("known", "tap")


@pytest.mark.parametrize(
    "frame",
    [
        "not json",
        "[]",
        '{"type": "nope"}',
        '{"type": "transcript", "text": 5}',
        '{"type": "time.ping"}',
        '{"type": "time.ping", "t0": 1e400}',
    ],
)
def test_bad_input_gets_an_error_event_and_the_socket_stays_open(room, frame: str) -> None:
    ana, ben = room

    ana.send_text(frame)

    error = ana.receive_json()
    assert (error["type"], error["code"]) == ("error", "bad_event")
    assert frame not in error["message"]
    ana.send_json(TRANSCRIPT)
    assert ben.receive_json()["utterance_id"] == "utt-1"


def test_knowledge_set_reports_a_store_that_is_too_far_behind(room, monkeypatch) -> None:
    ana, _ = room
    monkeypatch.setattr("confpilot.routes.ws.MAX_BACKGROUND_TASKS", 0)

    ana.send_json({"type": "knowledge.set", "term_id": "rag", "status": "known"})

    assert ana.receive_json()["code"] == "store_unavailable"


def test_binary_frames_get_an_error_event(room) -> None:
    ana, _ = room

    ana.send_bytes(b"\x00\x01")

    assert ana.receive_json()["code"] == "bad_event"


@pytest.mark.parametrize(
    "url",
    [
        "/ws/rooms/slc1?name=Ana&role=speaker",
        "/ws/rooms/slc1?user_id=u-ana&role=admin",
        "/ws/rooms/slc1?user_id=a/../b&role=speaker",
        "/ws/rooms/bad%20room!?user_id=u-ana",
        "/ws/rooms/slc1?user_id=" + "x" * 65,
    ],
)
def test_bad_join_parameters_are_refused_with_a_reason(client: TestClient, url: str) -> None:
    with client.websocket_connect(url) as socket:
        assert socket.receive_json()["code"] == "bad_request"
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
    assert closed.value.code == 1008


def test_server_heartbeat_resends_room_state(make_settings) -> None:
    with TestClient(create_app(make_settings(ws_heartbeat_s=0.05))) as fast:
        with fast.websocket_connect(ANA_URL) as ana:
            first, second = ana.receive_json(), ana.receive_json()

    assert first == second == {"type": "room.state", "members": [{**ANA, "role": "speaker"}]}
