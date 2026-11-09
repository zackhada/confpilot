"""A small in-memory sliding-window rate limit. One replica, so one process sees everything.

Which address is "the client" depends on what sits in front of the API, so it is configured:

- ``CLIENT_IP_HEADER`` unset: ``request.client``, the peer uvicorn reports. This is only the
  real client when uvicorn's ``--forwarded-allow-ips`` names the proxy; with ``*`` it is the
  leftmost X-Forwarded-For entry, which the caller controls.
- ``CLIENT_IP_HEADER`` set: that header, for an edge that overwrites it on every request,
  such as ``CF-Connecting-IP`` (Cloudflare) or ``CloudFront-Viewer-Address`` (CloudFront).
  Set it only when callers cannot reach the API without passing through that edge, otherwise
  the header is just another value the caller chooses.

This module never reads X-Forwarded-For itself, because any client can set that header.
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


def client_address(request: Request) -> str:
    """The address to rate limit by: the configured edge header, else the peer."""
    header: str = request.app.state.settings.client_ip_header
    value = request.headers.get(header, "").strip() if header else ""
    if value and header.lower() == "cloudfront-viewer-address":
        value = value.rpartition(":")[0]  # "ip:port", and the port changes per connection
    if value:
        return value[:64]
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, scope: str, user_id: str | None = None) -> None:
    """Raise 429 when this client address, or this user, is over the limit for ``scope``."""
    limiter: RateLimiter = request.app.state.rate_limiter
    keys = [f"{scope}:ip:{client_address(request)}"]
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
