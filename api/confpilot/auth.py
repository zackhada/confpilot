"""Signed sessions: the server issues the user id, so identity is never client-claimed.

A session is ``base64url(payload).base64url(HMAC-SHA256(payload))`` where the payload is the
JSON ``{"user_id": ..., "exp": <epoch ms>}``. It is not encrypted and holds nothing secret.
"""

import base64
import binascii
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
import uuid

from pydantic import SecretStr

from confpilot.models import SAFE_ID_PATTERN

SESSION_TTL_S = 12 * 60 * 60
MAX_SESSION_CHARS = 512
MIN_SECRET_CHARS = 16

_SAFE_ID = re.compile(SAFE_ID_PATTERN)
_log = logging.getLogger(__name__)


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class SessionSigner:
    def __init__(self, secret: bytes, ttl_s: int = SESSION_TTL_S) -> None:
        self._secret = secret
        self._ttl_ms = ttl_s * 1000

    @classmethod
    def from_setting(cls, secret: SecretStr | None, ttl_s: int = SESSION_TTL_S) -> "SessionSigner":
        """Use SESSION_SECRET, or a random key (with a warning) when it is not set."""
        if secret is None:
            _log.warning(
                "SESSION_SECRET is not set: using a random key, so every session ends when "
                "this process restarts"
            )
            return cls(secrets.token_bytes(32), ttl_s)
        value = secret.get_secret_value()
        if len(value) < MIN_SECRET_CHARS:
            _log.warning("SESSION_SECRET is shorter than %d characters", MIN_SECRET_CHARS)
        return cls(value.encode("utf-8"), ttl_s)

    def _sign(self, payload: bytes) -> bytes:
        return hmac.new(self._secret, payload, hashlib.sha256).digest()

    def issue(self, user_id: str | None = None, now_ms: int | None = None) -> tuple[str, str, int]:
        """Return (user_id, session, expires_at in epoch ms). The user id is a new UUID4
        unless one is given (tests and re-issuing only)."""
        user_id = user_id or str(uuid.uuid4())
        now_ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
        expires_at = now_ms + self._ttl_ms
        payload = json.dumps({"user_id": user_id, "exp": expires_at}, separators=(",", ":"))
        raw = payload.encode("utf-8")
        return user_id, f"{_encode(raw)}.{_encode(self._sign(raw))}", expires_at

    def verify(self, session: str, now_ms: int | None = None) -> str | None:
        """The session's user id, or None if it is malformed, forged or expired."""
        if not session or len(session) > MAX_SESSION_CHARS or session.count(".") != 1:
            return None
        encoded_payload, encoded_signature = session.split(".")
        try:
            payload = _decode(encoded_payload)
            signature = _decode(encoded_signature)
        except (binascii.Error, ValueError):
            return None
        if not hmac.compare_digest(self._sign(payload), signature):  # constant time
            return None
        try:
            claims = json.loads(payload)
        except ValueError:
            return None
        user_id = claims.get("user_id") if isinstance(claims, dict) else None
        expires_at = claims.get("exp") if isinstance(claims, dict) else None
        now_ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
        if not isinstance(user_id, str) or not _SAFE_ID.fullmatch(user_id):
            return None
        if not isinstance(expires_at, int) or expires_at <= now_ms:
            return None
        return user_id
