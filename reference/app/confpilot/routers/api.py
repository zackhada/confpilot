"""ConfPilot HTTP API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..schemas import AskRequest, ChaosRequest, MatchRequest
from ..services import chaos, matching, rag, rooms, search
from ..services.llm import LLMUnavailable

router = APIRouter(prefix="/api", tags=["ConfPilot"])


@router.get("/search")
def api_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    k: int | None = Query(default=None, ge=1, le=50),
    mode: str = Query(default="hybrid", pattern="^(hybrid|bm25|vector)$"),
):
    """Hybrid (BM25 + vector) talk search against the ``talks`` index."""
    return search.hybrid_search(q, k=k, mode=mode)


@router.post("/ask")
def api_ask(body: AskRequest):
    """RAG: retrieve relevant talks, then answer with an OpenAI-compatible LLM."""
    try:
        return rag.ask(
            body.question,
            history=body.history,
            top_k=body.top_k,
            plain_language=body.plain_language,
        )
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/match")
def api_match(body: MatchRequest):
    """Hallway matchmaker: find attendees with similar interests."""
    if not body.interests and body.vector is None:
        raise HTTPException(status_code=422, detail="Provide 'interests' or 'vector'")
    return matching.match(
        interests=body.interests,
        vector=body.vector,
        limit=body.limit,
        self_id=body.self_id,
    )


@router.get("/rooms")
def api_rooms(room: str | None = Query(default=None)):
    """Current crowd levels per room (including the sensory-friendly quiet room)."""
    return {"rooms": rooms.get_rooms(room=room)}


@router.get("/chaos")
def api_chaos_get():
    """Read the current chaos (latency/error injection) state."""
    return chaos.get_state()


@router.post("/chaos")
def api_chaos_post(body: ChaosRequest):
    """Update chaos state. Omit a field to leave it unchanged."""
    return chaos.set_state(
        enabled=body.enabled,
        latency_ms=body.latency_ms,
        error_rate=body.error_rate,
    )
