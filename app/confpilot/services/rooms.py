"""Crowd levels per room (quiet-room indicator). Uses ES ``rooms`` if available."""
from __future__ import annotations

import logging
import time

from opentelemetry import metrics

from .. import config
from ..elasticsearch_client import get_es

log = logging.getLogger("confpilot.rooms")

meter = metrics.get_meter("confpilot.rooms")
occupancy_gauge = meter.create_up_down_counter(
    "confpilot.rooms.occupancy", "1", "current occupancy per room"
)

SAMPLE_ROOMS: list[dict] = [
    {"id": "r1", "name": "Grand Ballroom A", "floor": "1", "capacity": 400, "current_count": 210, "quiet": False},
    {"id": "r2", "name": "Breakout 2", "floor": "1", "capacity": 80, "current_count": 78, "quiet": False},
    {"id": "r3", "name": "Quiet Room", "floor": "2", "capacity": 40, "current_count": 12, "quiet": True},
    {"id": "r4", "name": "Expo Hall", "floor": "1", "capacity": 600, "current_count": 480, "quiet": False},
    {"id": "r5", "name": "Workshop C", "floor": "2", "capacity": 50, "current_count": 22, "quiet": False},
]


def crowd_level(count: int, capacity: int) -> str:
    if capacity <= 0:
        return "unknown"
    ratio = count / capacity
    if ratio < 0.25:
        return "low"
    if ratio < 0.6:
        return "medium"
    if ratio < 0.9:
        return "high"
    return "full"


def _from_es() -> list[dict] | None:
    es = get_es()
    if es is None:
        return None
    try:
        resp = es.search(index=config.ES_INDEX_ROOMS, body={"size": 100})
        return [hit.get("_source", {}) for hit in resp.get("hits", {}).get("hits", [])]
    except Exception as exc:  # noqa: BLE001 - fall back to sample
        log.warning("Rooms lookup failed (%s); using local sample", exc)
        return None


def get_rooms(room: str | None = None) -> list[dict]:
    rooms = _from_es() or SAMPLE_ROOMS
    if room:
        needle = room.strip().lower()
        rooms = [
            r
            for r in rooms
            if (r.get("id") or "").lower() == needle or (r.get("name") or "").lower() == needle
        ]

    now = time.time()
    out: list[dict] = []
    for r in rooms:
        capacity = int(r.get("capacity", 0))
        count = int(r.get("current_count", 0))
        level = crowd_level(count, capacity)
        occupancy_gauge.add(count, {"room": r.get("name", "unknown"), "floor": r.get("floor", "unknown")})
        out.append({**r, "crowd_level": level, "updated_at": now})
    return out
