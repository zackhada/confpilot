"""Pydantic mirrors of contracts/types.ts. JSON keys are snake_case; timestamps are epoch ms."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

KnowledgeStatus = Literal["unknown", "learning", "known"]
KnowledgeSource = Literal["probe", "tap", "srs", "seed"]


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


class Glossary(BaseModel):
    # content/glossary.json writes the version as a number; the contract (and the API) use a string.
    model_config = ConfigDict(coerce_numbers_to_str=True)

    version: str
    terms: list[Term]


class Knowledge(BaseModel):
    user_id: str
    term_id: str
    status: KnowledgeStatus = "unknown"
    source: KnowledgeSource = "tap"
    encounters: int = 0
    ease: float = 2.5
    interval_days: float = 0
    reps: int = 0
    due_at: int | None = None
    learned: bool = False


class KnowledgePatch(BaseModel):
    """Any subset of the Knowledge fields except the two ids."""

    model_config = ConfigDict(extra="forbid")

    status: KnowledgeStatus | None = None
    source: KnowledgeSource | None = None
    encounters: int | None = None
    ease: float | None = None
    interval_days: float | None = None
    reps: int | None = None
    due_at: int | None = None
    learned: bool | None = None


class Speaker(BaseModel):
    user_id: str
    name: str


class SearchHit(BaseModel):
    utterance_id: str
    speaker: Speaker
    spoken_at: int
    text: str
    highlight: str
    term_ids: list[str]


class HeardTerm(BaseModel):
    term_id: str
    count: int


class Recap(BaseModel):
    room: str
    new_term_count: int
    heard: list[HeardTerm]
    learn_next: list[str]
