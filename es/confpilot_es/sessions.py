"""One session document per room: when it started, when it was last active, and who spoke."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from confpilot_es.base import StoreBase
from confpilot_es.models import RoomSession, Speaker
from confpilot_es.telemetry import es_span

# Runs inside Elasticsearch, so two phones reporting at the same moment cannot lose an update.
_TOUCH_SCRIPT = """
if (params.at > ctx._source.last_at) { ctx._source.last_at = params.at }
if (params.at < ctx._source.started_at) { ctx._source.started_at = params.at }
if (params.speaker != null) {
  boolean present = false;
  for (def speaker : ctx._source.speakers) {
    if (speaker.user_id == params.speaker.user_id) { present = true }
  }
  if (!present) { ctx._source.speakers.add(params.speaker) }
}
"""


class SessionMixin(StoreBase):
    async def touch_session(self, room: str, speaker: Speaker | Mapping[str, Any] | None, at: int) -> RoomSession:
        """Create the room's session if needed, then record activity at `at` and the speaker.

        One scripted upsert, keyed by the room code. `at` is epoch milliseconds in server time.
        """
        who = Speaker.model_validate(speaker).model_dump() if speaker is not None else None
        created = {
            "session_id": room,
            "room": room,
            "started_at": at,
            "last_at": at,
            "speakers": [who] if who else [],
        }
        with es_span("es.index", operation="touch_session", room=room):
            response = await self.client.update(
                index=self.index("sessions"),
                id=room,
                script={"source": _TOUCH_SCRIPT, "lang": "painless", "params": {"at": at, "speaker": who}},
                upsert=created,
                source=True,
                refresh=self.refresh,
                retry_on_conflict=5,
            )
        return RoomSession.model_validate(response["get"]["_source"])

    async def get_session(self, room: str) -> RoomSession | None:
        """The room's session, or None if nothing has happened there."""
        with es_span("es.get", operation="get_session", room=room):
            response = await self.client.options(ignore_status=404).get(index=self.index("sessions"), id=room)
        if not response.get("found"):
            return None
        return RoomSession.model_validate(response["_source"])
