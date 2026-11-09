"""Pydantic mirrors of contracts/types.ts. JSON keys are snake_case; timestamps are epoch ms."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Term(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    term: str
    aliases: list[str]
    say: str | None = None
    category: str
    level: Literal[1, 2, 3, 4]
    simple_def: str
    long_def: str | None = None
    example: str | None = None
    prereqs: list[str]
    translations: dict[str, str] | None = None
    ambiguous: bool | None = None
    context: list[str] | None = None
    source: Literal["seed", "llm"]
