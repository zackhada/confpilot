"""In-memory room hub. It lives in this process, so the API runs as exactly one replica."""

import asyncio
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel
from starlette.websockets import WebSocket, WebSocketDisconnect

from confpilot.models import Member, RoomState, Speaker

OUTBOX_SIZE = 256

_log = logging.getLogger(__name__)


@dataclass(eq=False)
class Connection:
    """One socket. Sending only queues, so a phone on bad wifi never slows the room down."""

    websocket: WebSocket
    room: str
    member: Member
    outbox: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(OUTBOX_SIZE))
    dropped: int = 0

    @property
    def speaker(self) -> Speaker:
        return Speaker(user_id=self.member.user_id, name=self.member.name)

    def send(self, event: BaseModel) -> None:
        self.send_raw(event.model_dump_json())

    def send_raw(self, payload: str) -> None:
        try:
            self.outbox.put_nowait(payload)
        except asyncio.QueueFull:
            self.dropped += 1
            if self.dropped == 1:
                _log.warning(
                    "outbox full, dropping events for a slow client",
                    extra={"confpilot.room": self.room, "confpilot.user_id": self.member.user_id},
                )

    async def pump(self) -> None:
        """Write queued events to the socket until cancelled or the socket fails."""
        try:
            while True:
                await self.websocket.send_text(await self.outbox.get())
                self.dropped = 0  # caught up: warn again if it stalls again
        except (WebSocketDisconnect, RuntimeError, OSError) as exc:
            # The receive loop sees the same disconnect and cleans up.
            _log.debug("socket closed while sending: %s", exc)


class Hub:
    def __init__(self) -> None:
        self._rooms: dict[str, list[Connection]] = {}
        self._ever: dict[str, set[str]] = {}  # room -> user ids that have joined it

    def was_member(self, room: str, user_id: str) -> bool:
        """Has this user joined the room, now or earlier, since this process started?"""
        return user_id in self._ever.get(room, ())

    def join(self, connection: Connection) -> None:
        self._rooms.setdefault(connection.room, []).append(connection)
        self._ever.setdefault(connection.room, set()).add(connection.member.user_id)
        self.broadcast(connection.room, self.state(connection.room))

    def leave(self, connection: Connection) -> None:
        remaining = [c for c in self._rooms.get(connection.room, []) if c is not connection]
        if remaining:
            self._rooms[connection.room] = remaining
            self.broadcast(connection.room, self.state(connection.room))
        else:
            self._rooms.pop(connection.room, None)

    def state(self, room: str) -> RoomState:
        """Current members, one entry per user even if they have two tabs open."""
        members = {c.member.user_id: c.member for c in self._rooms.get(room, [])}
        return RoomState(members=list(members.values()))

    def broadcast(self, room: str, event: BaseModel, exclude: Connection | None = None) -> int:
        """Queue ``event`` for everyone in the room except ``exclude``. Returns the count."""
        payload = event.model_dump_json()
        recipients = [c for c in self._rooms.get(room, []) if c is not exclude]
        for connection in recipients:
            connection.send_raw(payload)
        return len(recipients)
