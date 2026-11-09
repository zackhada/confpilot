"""User knowledge, room recap and transcript search. All of it reads and writes the Store."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request

from confpilot.auth import CurrentUser, require_same_user
from confpilot.models import (
    SAFE_ID_PATTERN,
    Glossary,
    HeardTerm,
    Knowledge,
    KnowledgeList,
    KnowledgePatch,
    Recap,
    SearchResponse,
)
from confpilot.store import Store
from confpilot.telemetry import tracer

LEARN_NEXT_LIMIT = 10

IdPath = Annotated[str, Path(pattern=SAFE_ID_PATTERN)]
IdQuery = Annotated[str | None, Query(pattern=SAFE_ID_PATTERN)]

router = APIRouter(prefix="/api")


def require_member(request: Request, room: str, user_id: str) -> None:
    """Transcripts are only for people who are, or were, in the room."""
    if not request.app.state.hub.was_member(room, user_id):
        raise HTTPException(status_code=403, detail="Join this room before reading from it")


def build_recap(
    room: str, counts: dict[str, int], knowledge: list[Knowledge], glossary: Glossary
) -> Recap:
    """Rank what was heard. A term is on the frontier when all its prerequisites are known."""
    known = {k.term_id for k in knowledge if k.status == "known" or k.learned}
    prereqs = {term.id: term.prereqs for term in glossary.terms}
    heard = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    new = [(term_id, count) for term_id, count in heard if term_id not in known]

    def rank(item: tuple[str, int]) -> tuple[int, int, str]:
        term_id, count = item
        on_frontier = all(p in known for p in prereqs.get(term_id, []))
        return (-count * on_frontier, -count, term_id)

    return Recap(
        room=room,
        new_term_count=len(new),
        heard=[HeardTerm(term_id=term_id, count=count) for term_id, count in heard],
        learn_next=[term_id for term_id, _ in sorted(new, key=rank)][:LEARN_NEXT_LIMIT],
    )


@router.get("/users/{user_id}/knowledge", response_model=KnowledgeList)
async def list_knowledge(request: Request, user_id: IdPath, user: CurrentUser) -> KnowledgeList:
    require_same_user(user_id, user)
    store: Store = request.app.state.store
    with tracer.start_as_current_span(
        "knowledge.list", attributes={"confpilot.user_id": user_id}
    ) as span:
        items = await store.get_knowledge(user_id)
        span.set_attribute("confpilot.knowledge.count", len(items))
        return KnowledgeList(items=items)


@router.put("/users/{user_id}/knowledge/{term_id}", response_model=Knowledge)
async def put_knowledge(
    request: Request, user_id: IdPath, term_id: IdPath, patch: KnowledgePatch, user: CurrentUser
) -> Knowledge:
    require_same_user(user_id, user)
    store: Store = request.app.state.store
    attributes = {"confpilot.user_id": user_id, "confpilot.term_id": term_id}
    with tracer.start_as_current_span("knowledge.put", attributes=attributes) as span:
        knowledge = await store.put_knowledge(user_id, term_id, patch)
        span.set_attribute("confpilot.knowledge.status", knowledge.status)
        return knowledge


@router.get("/rooms/{room}/recap", response_model=Recap)
async def get_recap(
    request: Request, room: IdPath, user: CurrentUser, user_id: IdQuery = None
) -> Recap:
    """The recap is always personal: it is ranked against the session user's knowledge."""
    require_same_user(user_id, user)
    require_member(request, room, user)
    store: Store = request.app.state.store
    attributes = {"confpilot.room": room, "confpilot.user_id": user}
    with tracer.start_as_current_span("room.recap", attributes=attributes) as span:
        counts = await store.term_counts(room)
        knowledge = await store.get_knowledge(user)
        recap = build_recap(room, counts, knowledge, request.app.state.glossary)
        span.set_attribute("confpilot.recap.heard_count", len(recap.heard))
        span.set_attribute("confpilot.recap.new_term_count", recap.new_term_count)
        return recap


@router.get("/search", response_model=SearchResponse)
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    room: Annotated[str, Query(pattern=SAFE_ID_PATTERN)],
    user: CurrentUser,
    user_id: IdQuery = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    require_same_user(user_id, user)
    require_member(request, room, user)
    store: Store = request.app.state.store
    attributes = {"confpilot.search.query_length": len(q), "confpilot.room": room}
    with tracer.start_as_current_span("search", attributes=attributes) as span:
        hits = await store.search(q, room=room, limit=limit)
        span.set_attribute("confpilot.search.hit_count", len(hits))
        return SearchResponse(hits=hits)
