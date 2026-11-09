"""Pydantic mirrors of contracts/types.ts. That file is the source of truth."""

import math
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    TypeAdapter,
    model_serializer,
)

# room, user_id and term_id travel in URLs, log lines and metric attributes.
SAFE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SafeId = Annotated[str, StringConstraints(pattern=SAFE_ID_PATTERN)]
# Ids minted on the phone (utterances, cards): a little looser, still bounded.
EventId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")]


def _round_ms(value: object) -> object:
    """Browsers produce fractional milliseconds. The wire type is whole epoch ms."""
    return round(value) if isinstance(value, float) and math.isfinite(value) else value


Ms = Annotated[int, BeforeValidator(_round_ms), Field(ge=0)]
Finite = Annotated[float, Field(allow_inf_nan=False)]  # JSON has no Infinity or NaN


class WireModel(BaseModel):
    """Serializes like the TypeScript type: `x?: T` fields are left out when unset, while
    `x: T | null` fields stay in the output as null."""

    omit_when_none: ClassVar[frozenset[str]] = frozenset()

    @model_serializer(mode="wrap")
    def _omit_unset_optionals(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        return {k: v for k, v in data.items() if v is not None or k not in self.omit_when_none}


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class TokenRequest(BaseModel):
    user_id: SafeId


class TokenResponse(BaseModel):
    provider: Literal["deepgram"] = "deepgram"
    token: str  # short-lived; open ws_url with new WebSocket(ws_url, ["bearer", token])
    expires_in_s: int
    ws_url: str  # full streaming URL including model, encoding and keyterms


class ProbeRequest(BaseModel):
    user_id: SafeId
    transcript: str = Field(max_length=8000)


class ProbeResponse(BaseModel):
    role: str
    domain: str
    known_term_ids: list[str]
    english_level: Literal["A2", "B1", "B2", "C1", "C2"]
    goals: list[str]


# ---------- Glossary ----------

Lang = Literal["es", "zh", "hi", "pt"]


class Term(WireModel):
    omit_when_none = frozenset({"long_def", "example", "translations", "ambiguous", "context"})

    id: str
    term: str
    aliases: list[str] = []  # as written; the matcher normalizes them
    say: str | None = None  # pronunciation hint; null when it is obvious
    category: str = ""
    level: Literal[1, 2, 3, 4]
    simple_def: str
    long_def: str | None = None
    example: str | None = None
    prereqs: list[str] = []
    translations: dict[Lang, str] | None = None
    ambiguous: bool | None = None
    context: list[str] | None = None
    source: Literal["seed", "llm"] = "seed"


class Glossary(BaseModel):
    """content/glossary.json also carries `generated` and `levels`; they are not served."""

    version: Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, int) else v)]
    terms: list[Term]


# ---------- User knowledge (SM-2) ----------

KnowledgeStatus = Literal["unknown", "learning", "known"]
KnowledgeSource = Literal["probe", "tap", "srs", "seed"]


class Knowledge(BaseModel):
    user_id: SafeId
    term_id: SafeId
    status: KnowledgeStatus = "unknown"
    source: KnowledgeSource = "tap"
    encounters: int = Field(default=0, ge=0)
    ease: float = Field(default=2.5, ge=1.0, le=5.0)
    interval_days: float = Field(default=0, ge=0)
    reps: int = Field(default=0, ge=0)
    due_at: Ms | None = None
    learned: bool = False  # true once interval_days >= 7


class KnowledgePatch(BaseModel):
    """Partial<Omit<Knowledge, "user_id" | "term_id">>. Unknown keys are ignored."""

    status: KnowledgeStatus | None = None
    source: KnowledgeSource | None = None
    encounters: int | None = Field(default=None, ge=0)
    ease: float | None = Field(default=None, ge=1.0, le=5.0)
    interval_days: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    due_at: Ms | None = None
    learned: bool | None = None


class KnowledgeList(BaseModel):
    items: list[Knowledge]


# ---------- Room WebSocket events ----------

Role = Literal["speaker", "viewer"]
CardTier = Literal[1, 2, 3]


class Speaker(BaseModel):
    user_id: SafeId
    name: str = Field(max_length=80)


class Member(Speaker):
    role: Role


class Word(BaseModel):
    w: str = Field(max_length=100)
    start_ms: Finite = Field(ge=0)
    end_ms: Finite = Field(ge=0)


class TranscriptEvent(WireModel):
    omit_when_none = frozenset({"speaker"})

    type: Literal["transcript"] = "transcript"
    utterance_id: EventId
    seq: int = Field(ge=0)
    is_final: bool
    text: str = Field(max_length=4000)
    words: list[Word] = Field(max_length=600)
    started_at: Ms
    speaker: Speaker | None = None  # set by the server on relay


class ServerCardEvent(BaseModel):
    type: Literal["card"] = "card"
    tier: Literal[2, 3]
    term: Term
    utterance_id: EventId
    spoken_at: Ms


class CardShownEvent(WireModel):
    omit_when_none = frozenset({"user"})

    type: Literal["card.shown"] = "card.shown"
    card_id: EventId
    term_id: SafeId
    tier: CardTier
    utterance_id: EventId
    spoken_at: Ms
    rendered_at: Ms
    word_to_card_ms: Finite
    user: Speaker | None = None  # set by the server on relay


class KnowledgeSetEvent(BaseModel):
    type: Literal["knowledge.set"] = "knowledge.set"
    term_id: SafeId
    status: KnowledgeStatus


class TimePing(BaseModel):
    type: Literal["time.ping"] = "time.ping"
    t0: Finite


class TimePong(BaseModel):
    type: Literal["time.pong"] = "time.pong"
    t0: Finite
    server_ts: Ms


class RoomState(BaseModel):
    type: Literal["room.state"] = "room.state"
    members: list[Member]


ErrorCode = Literal["bad_request", "bad_event", "forbidden", "store_unavailable", "internal"]


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: ErrorCode
    message: str


ClientEvent = Annotated[
    TranscriptEvent | CardShownEvent | KnowledgeSetEvent | TimePing, Field(discriminator="type")
]
ServerEvent = TranscriptEvent | ServerCardEvent | CardShownEvent | TimePong | RoomState | ErrorEvent
client_event_adapter: TypeAdapter[ClientEvent] = TypeAdapter(ClientEvent)


# ---------- Stored and searched ----------


class Utterance(BaseModel):
    """A final transcript as stored. Not in contracts: it never crosses to the browser."""

    utterance_id: EventId
    room: SafeId
    speaker: Speaker
    spoken_at: Ms  # server-time ms when the utterance's audio began
    text: str
    term_ids: list[str] = []


class RoomSession(BaseModel):
    """Metadata for one room's conversation. Not in contracts."""

    room: SafeId
    started_at: Ms
    last_at: Ms
    speakers: list[Speaker] = []


class SearchHit(BaseModel):
    utterance_id: str
    speaker: Speaker
    spoken_at: Ms
    text: str
    highlight: str  # HTML-escaped text with <mark> around matches
    term_ids: list[str]


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class HeardTerm(BaseModel):
    term_id: str
    count: int


class Recap(BaseModel):
    room: str
    new_term_count: int
    heard: list[HeardTerm]  # most heard first
    learn_next: list[str]  # term ids, ranked by heard count x on-frontier
