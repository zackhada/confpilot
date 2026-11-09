"""Room WebSocket: /ws/rooms/{room}?session=&name=&role=  (contracts/README.md section 1)."""

import asyncio
import logging
import time
from collections.abc import Coroutine

from fastapi import APIRouter, WebSocket
from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel, Field, ValidationError
from starlette.datastructures import State
from starlette.websockets import WebSocketDisconnect

from confpilot.auth import INVALID, origin_allowed
from confpilot.models import (
    CardShownEvent,
    ErrorEvent,
    KnowledgePatch,
    KnowledgeSetEvent,
    Member,
    Role,
    SafeId,
    TimePing,
    TimePong,
    TranscriptEvent,
    client_event_adapter,
)
from confpilot.rooms import Connection, Hub
from confpilot.telemetry import tracer, word_to_card_ms
from confpilot.utterances import store_final_or_release, transcript_words

MAX_FRAME_CHARS = 128_000
MAX_RECORDED_LATENCY_MS = 60_000  # beyond this a clock is wrong, keep it out of the SLI
MAX_BACKGROUND_TASKS = 500

router = APIRouter()
_log = logging.getLogger(__name__)
_background: set[asyncio.Task[None]] = set()


class JoinParams(BaseModel):
    room: SafeId
    user_id: SafeId
    name: str = Field(max_length=80)
    role: Role


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def _describe(exc: ValidationError) -> str:
    """The first problem, without echoing the client's input back."""
    first = exc.errors(include_input=False, include_url=False)[0]
    where = ".".join(str(part) for part in first["loc"])
    return f"{where}: {first['msg']}" if where else first["msg"]


def spawn(work: Coroutine[None, None, None], what: str) -> bool:
    """Run storage work off the receive loop, so a slow store never delays the next relay.

    Returns False, and drops the work, when the store is so far behind that queueing more
    would only grow memory.
    """
    if len(_background) >= MAX_BACKGROUND_TASKS:
        work.close()
        _log.warning("store is behind, dropping %s", what)
        return False

    def done(task: asyncio.Task[None]) -> None:
        _background.discard(task)
        if not task.cancelled() and task.exception() is not None:
            _log.error("background %s failed", what, exc_info=task.exception())

    task = asyncio.create_task(work)
    _background.add(task)
    task.add_done_callback(done)
    return True


async def _heartbeat(hub: Hub, connection: Connection, every_s: float) -> None:
    """Keep idle load balancers from closing the socket, and re-sync the member list."""
    while True:
        await asyncio.sleep(every_s)
        connection.send(hub.state(connection.room))


def handle_transcript(state: State, connection: Connection, event: TranscriptEvent) -> None:
    hub: Hub = state.hub
    attributes = {
        "confpilot.room": connection.room,
        "confpilot.user_id": connection.member.user_id,
        "confpilot.utterance.is_final": event.is_final,
        "confpilot.utterance.seq": event.seq,
    }
    with tracer.start_as_current_span("transcript.relay", attributes=attributes) as span:
        if connection.member.role != "speaker":
            connection.send(ErrorEvent(code="forbidden", message="Only speakers send transcripts"))
            return
        relayed = event.model_copy(update={"speaker": connection.speaker})
        count = hub.broadcast(connection.room, relayed, exclude=connection)  # relay comes first
        span.set_attribute("confpilot.room.recipients", count)
        if not event.is_final:
            return
        # Storage work starts only now, after the relay is queued.
        words = transcript_words(event)
        admitted_at = time.monotonic()
        fresh = state.recent_finals.admit(
            connection.room, connection.member.user_id, words, admitted_at
        )
        span.set_attribute("confpilot.utterance.duplicate", not fresh)
        if not fresh:
            return
        storing = store_final_or_release(
            state.store,
            state.matcher,
            state.recent_finals,
            connection.room,
            relayed,
            words,
            admitted_at,
        )
        if not spawn(storing, "store_final"):
            state.recent_finals.forget(
                connection.room, connection.member.user_id, words, admitted_at
            )
            span.set_attribute("confpilot.utterance.store_dropped", True)


def handle_card_shown(hub: Hub, connection: Connection, event: CardShownEvent) -> None:
    attributes = {
        "confpilot.room": connection.room,
        "confpilot.user_id": connection.member.user_id,
        "confpilot.card.tier": event.tier,
        "confpilot.card.term_id": event.term_id,
        "confpilot.card.word_to_card_ms": event.word_to_card_ms,
    }
    with tracer.start_as_current_span("card.push", attributes=attributes):
        shown = event.model_copy(update={"user": connection.speaker})
        hub.broadcast(connection.room, shown, exclude=connection)
        if 0 <= event.word_to_card_ms <= MAX_RECORDED_LATENCY_MS:
            # Tier only: a room id is chosen by clients, so it would be an unbounded label.
            word_to_card_ms.record(event.word_to_card_ms, {"confpilot.card.tier": event.tier})


async def save_knowledge(
    websocket: WebSocket, connection: Connection, event: KnowledgeSetEvent
) -> None:
    attributes = {
        "confpilot.room": connection.room,
        "confpilot.user_id": connection.member.user_id,
        "confpilot.term_id": event.term_id,
        "confpilot.knowledge.status": event.status,
    }
    with tracer.start_as_current_span("knowledge.set", attributes=attributes) as span:
        patch = KnowledgePatch(status=event.status, source="tap")
        try:
            await websocket.app.state.store.put_knowledge(
                connection.member.user_id, event.term_id, patch
            )
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, "store unavailable"))
            _log.exception("knowledge.set could not be saved")
            connection.send(ErrorEvent(code="store_unavailable", message="Could not save that"))


def handle(websocket: WebSocket, connection: Connection, raw: str | None) -> None:
    hub: Hub = websocket.app.state.hub
    if raw is None or len(raw) > MAX_FRAME_CHARS:
        connection.send(ErrorEvent(code="bad_event", message="Send one JSON text frame per event"))
        return
    try:
        event = client_event_adapter.validate_json(raw)
    except ValidationError as exc:
        connection.send(ErrorEvent(code="bad_event", message=_describe(exc)))
        return
    if isinstance(event, TranscriptEvent):
        handle_transcript(websocket.app.state, connection, event)
    elif isinstance(event, CardShownEvent):
        handle_card_shown(hub, connection, event)
    elif isinstance(event, KnowledgeSetEvent):
        if not spawn(save_knowledge(websocket, connection, event), "knowledge.set"):
            connection.send(ErrorEvent(code="store_unavailable", message="Could not save that"))
    elif isinstance(event, TimePing):
        attributes = {"confpilot.room": connection.room}
        with tracer.start_as_current_span("time.ping", attributes=attributes):
            connection.send(TimePong(t0=event.t0, server_ts=now_ms()))


@router.websocket("/ws/rooms/{room}")
async def room_socket(
    websocket: WebSocket, room: str, session: str = "", name: str = "", role: str = "speaker"
) -> None:
    state = websocket.app.state
    if not origin_allowed(websocket.headers, state.allowed_origins):
        await websocket.close(code=1008)  # before accept: the handshake is refused with 403
        return
    await websocket.accept()
    user_id = state.signer.verify(session)
    if user_id is None:
        error = ErrorEvent(code="unauthorized", message=INVALID)
        await websocket.send_text(error.model_dump_json())
        await websocket.close(code=1008)
        return
    try:
        clean_name = "".join(c for c in name if c.isprintable()).strip() or "Guest"
        params = JoinParams(room=room, user_id=user_id, name=clean_name, role=role)
    except ValidationError as exc:
        error = ErrorEvent(code="bad_request", message=_describe(exc))
        await websocket.send_text(error.model_dump_json())
        await websocket.close(code=1008)
        return

    hub: Hub = state.hub
    member = Member(user_id=params.user_id, name=params.name, role=params.role)
    connection = Connection(websocket=websocket, room=params.room, member=member)
    attributes = {
        "confpilot.room": params.room,
        "confpilot.user_id": params.user_id,
        "confpilot.role": params.role,
    }
    with tracer.start_as_current_span("room.join", attributes=attributes):
        hub.join(connection)
    heartbeat_s = state.settings.ws_heartbeat_s
    helpers = [
        asyncio.create_task(connection.pump()),
        asyncio.create_task(_heartbeat(hub, connection, heartbeat_s)),
    ]
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            try:
                handle(websocket, connection, message.get("text"))
            except Exception:
                _log.exception("room event failed", extra={"confpilot.room": params.room})
                connection.send(ErrorEvent(code="internal", message="That event failed"))
    except WebSocketDisconnect:
        pass  # the client went away mid-receive
    finally:
        for helper in helpers:
            helper.cancel()
        with tracer.start_as_current_span("room.leave", attributes=attributes):
            hub.leave(connection)
