"""A small in-memory sliding-window rate limit. One replica, so one process sees everything.

The client address prefers Cloudflare's ``CF-Connecting-IP`` header, which is overwritten by
Cloudflare because all traffic arrives through its tunnel, then falls back to
``request.client``. This module never reads X-Forwarded-For itself, because any client can set
that header.
"""

import math
import time
from collections import deque

from fastapi import HTTPException, Request

WINDOW_S = 60.0
SWEEP_AT_KEYS = 10_000


class RateLimiter:
    def __init__(self, limit: int, window_s: float = WINDOW_S) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, now: float) -> float:
        """Count one request. Returns 0 if it is allowed, else the seconds to wait."""
        if len(self._hits) >= SWEEP_AT_KEYS:
            cutoff = now - self.window_s
            self._hits = {k: v for k, v in self._hits.items() if v and v[-1] > cutoff}
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window_s:
            hits.popleft()
        if len(hits) >= self.limit:
            return hits[0] + self.window_s - now
        hits.append(now)
        return 0.0


def enforce_rate_limit(request: Request, scope: str, user_id: str | None = None) -> None:
    """Raise 429 when this client address, or this user, is over the limit for ``scope``."""
    limiter: RateLimiter = request.app.state.rate_limiter
    address = request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else "unknown"
    )
    keys = [f"{scope}:ip:{address}"]
    if user_id is not None:
        keys.append(f"{scope}:user:{user_id}")
    now = time.monotonic()
    for key in keys:
        wait_s = limiter.hit(key, now)
        if wait_s > 0:
            seconds = max(1, math.ceil(wait_s))
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {seconds} seconds.",
                headers={"Retry-After": str(seconds)},
            )
