"""Pydantic mirrors of contracts/types.ts. That file is the source of truth."""

from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, BeforeValidator, SerializerFunctionWrapHandler, model_serializer


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
