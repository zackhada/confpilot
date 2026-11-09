"""Request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1, le=50)
    plain_language: bool = False


class MatchRequest(BaseModel):
    interests: list[str] | None = None
    vector: list[float] | None = None
    limit: int = Field(default=10, ge=1, le=100)
    self_id: str | None = None


class ChaosRequest(BaseModel):
    enabled: bool | None = None
    latency_ms: int | None = Field(default=None, ge=0, le=60_000)
    error_rate: float | None = Field(default=None, ge=0.0, le=1.0)
