"""Pydantic mirrors of contracts/types.ts. That file is the source of truth."""

from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

# room, user_id and term_id travel in URLs, log lines and metric attributes.
SAFE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SafeId = Annotated[str, StringConstraints(pattern=SAFE_ID_PATTERN)]


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
