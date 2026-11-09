"""RAG assistant: retrieve top talks from Elasticsearch, then answer with an LLM."""
from __future__ import annotations

import logging

from opentelemetry import metrics, trace

from .. import config
from . import llm, search

log = logging.getLogger("confpilot.rag")

tracer = trace.get_tracer("confpilot.rag")
meter = metrics.get_meter("confpilot.rag")

rag_counter = meter.create_counter("confpilot.rag.requests", "1", "RAG requests")

SYSTEM_PROMPT = (
    "You are ConfPilot, an accessible AI conference companion. "
    "Answer using ONLY the provided talk abstracts and metadata. "
    "Cite talks by their title when relevant. "
    "Write in short, clear, plain-language sentences. "
    "If the provided talks do not contain the answer, say so and suggest a better search."
)

PLAIN_SYSTEM_PROMPT = (
    "You are ConfPilot, an accessible AI conference companion. "
    "Use very simple words and short sentences, like you are explaining to a wide audience. "
    "Avoid jargon and define any technical term you must use. "
    "Answer using ONLY the provided talks, and name the talk you are citing."
)


def _build_context(hits: list[dict]) -> str:
    if not hits:
        return "No matching talks were found in the conference index."
    parts = []
    for i, hit in enumerate(hits, 1):
        speakers = ", ".join(hit.get("speakers") or []) or "unknown"
        parts.append(
            f"[{i}] {hit.get('title')} — {speakers}\n"
            f"Track: {hit.get('track') or 'n/a'} | Room: {hit.get('room') or 'n/a'} | "
            f"Day/Time: {hit.get('day') or 'n/a'} {hit.get('start_time') or ''}\n"
            f"Abstract: {hit.get('abstract') or ''}\n"
            f"Tags: {', '.join(hit.get('tags') or [])}"
        )
    return "\n\n".join(parts)


def _sources(hits: list[dict]) -> list[dict]:
    keys = ("id", "title", "speakers", "room", "track", "day", "start_time", "score")
    return [{key: hit.get(key) for key in keys} for hit in hits]


def ask(
    question: str,
    history: list[dict] | None = None,
    top_k: int | None = None,
    plain_language: bool = False,
) -> dict:
    """Retrieve relevant talks and generate an answer grounded in them."""
    history = history or []
    top_k = top_k or config.RAG_TOP_K
    rag_counter.add(1)

    with tracer.start_as_current_span("rag.ask") as span:
        span.set_attribute("rag.question", question)
        span.set_attribute("rag.plain_language", plain_language)

        with tracer.start_as_current_span("rag.retrieve") as retrieve_span:
            results = search.hybrid_search(question, k=top_k, mode="hybrid")
            hits = results.get("hits", [])
            retrieve_span.set_attribute("rag.retrieved", len(hits))

        context = _build_context(hits)
        messages = [{"role": "system", "content": PLAIN_SYSTEM_PROMPT if plain_language else SYSTEM_PROMPT}]
        messages += [m for m in history if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Conference talks (search results):\n{context}\n\n"
                    f"Question: {question}"
                ),
            }
        )

        with tracer.start_as_current_span("rag.generate") as generate_span:
            answer, usage = llm.chat(messages)
            generate_span.set_attribute("rag.answer_length", len(answer))

        span.set_attribute("rag.sources", len(hits))
        return {"answer": answer, "sources": _sources(hits), "usage": usage}
