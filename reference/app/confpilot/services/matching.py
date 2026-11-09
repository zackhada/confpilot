"""Hallway matchmaker: rank attendees by interest-vector similarity.

Uses Elasticsearch kNN on the ``attendees`` index when available and falls
back to a deterministic local sample set (bag-of-words hash vectors).
"""
from __future__ import annotations

import hashlib
import logging
import math

from opentelemetry import metrics, trace

from .. import config
from ..elasticsearch_client import get_es

log = logging.getLogger("confpilot.match")

tracer = trace.get_tracer("confpilot.match")
meter = metrics.get_meter("confpilot.match")
match_counter = meter.create_counter("confpilot.match.requests", "1", "match requests")

VECTOR_DIM = 128
ATTENDEE_SOURCE_FIELDS = ["name", "title", "company", "interests"]


def interests_to_vector(interests: list[str], dim: int = VECTOR_DIM) -> list[float]:
    """Deterministic bag-of-words vector for a set of interest strings.

    Shared tokens produce shared components, so cosine similarity is positive
    when two people share interests. No embedding service required.
    """
    vec = [0.0] * dim
    for raw in interests or []:
        token = str(raw).strip().lower()
        if not token:
            continue
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(3):  # a few active components per token
            idx = int.from_bytes(digest[i * 4 : i * 4 + 4], "big") % dim
            sign = 1.0 if digest[(i * 4 + 4) % 32] % 2 == 0 else -1.0
            magnitude = 0.5 + digest[(i * 4 + 5) % 32] / 255.0
            vec[idx] += sign * magnitude
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity; assumes both vectors are L2-normalized."""
    return sum(x * y for x, y in zip(a, b))


_SAMPLE = [
    ("a1", "Ada Lovelace", "Platform Engineer", "NVIDIA", ["ebpf", "security", "kubernetes", "observability"]),
    ("a2", "Grace Hopper", "Compiler Engineer", "Red Hat", ["compilers", "wasm", "performance", "rust"]),
    ("a3", "Linus Torvalds", "Kernel Maintainer", "Linux Foundation", ["ebpf", "kernel", "security", "performance"]),
    ("a4", "Margaret Hamilton", "SRE", "Datadog", ["observability", "opentelemetry", "kubernetes", "sre"]),
    ("a5", "Alan Turing", "ML Engineer", "OpenAI", ["llm", "ml", "python", "rag"]),
    ("a6", "Radia Perlman", "Network Engineer", "Cisco", ["networking", "security", "routing", "ebpf"]),
    ("a7", "Katherine Johnson", "Data Scientist", "Snowflake", ["data", "sql", "ml", "analytics"]),
    ("a8", "Tim Berners-Lee", "Web Architect", "W3C", ["accessibility", "web", "standards", "a11y"]),
]

SAMPLE_ATTENDEES: list[dict] = [
    {
        "id": aid,
        "name": name,
        "title": title,
        "company": company,
        "interests": interests,
        "vector": interests_to_vector(interests),
    }
    for (aid, name, title, company, interests) in _SAMPLE
]


def _to_result(attendee: dict, similarity: float) -> dict:
    return {
        "id": attendee.get("id"),
        "name": attendee.get("name"),
        "title": attendee.get("title"),
        "company": attendee.get("company"),
        "interests": attendee.get("interests") or [],
        "similarity": round(float(similarity), 6),
    }


def _es_match(es, vector: list[float], limit: int, self_id: str | None) -> list[dict] | None:
    """kNN over ``attendees.interests_vector``; returns ``None`` on error/empty."""
    body = {
        "size": limit,
        "_source": ATTENDEE_SOURCE_FIELDS,
        "knn": {
            "field": "interests_vector",
            "query_vector": vector,
            "k": limit,
            "num_candidates": max(20, limit * 5),
        },
    }
    resp = es.search(index=config.ES_INDEX_ATTENDEES, body=body)
    hits = resp.get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        src = hit.get("_source", {}) or {}
        if self_id and src.get("id") == self_id:
            continue
        results.append(_to_result({**src, "id": hit.get("_id")}, hit.get("_score", 0.0)))
    return results or None


def _local_match(vector: list[float], limit: int, self_id: str | None) -> list[dict]:
    scored = []
    for attendee in SAMPLE_ATTENDEES:
        if self_id and attendee["id"] == self_id:
            continue
        scored.append((cosine(vector, attendee["vector"]), attendee))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [_to_result(a, sim) for sim, a in scored[:limit]]


def match(
    interests: list[str] | None = None,
    vector: list[float] | None = None,
    limit: int = 10,
    self_id: str | None = None,
) -> dict:
    """Match attendees to a target interest vector (from ``interests`` or ``vector``)."""
    match_counter.add(1)

    if vector is not None:
        vec = [float(x) for x in vector]
    elif interests:
        vec = interests_to_vector(interests)
    else:
        return {"matches": [], "backend": "none", "error": "Provide 'interests' or 'vector'"}

    with tracer.start_as_current_span("match.attendees") as span:
        span.set_attribute("match.dimensions", len(vec))
        span.set_attribute("match.limit", limit)

        backend = "local"
        results: list[dict] = []
        es = get_es()
        if es is not None:
            try:
                es_results = _es_match(es, vec, limit, self_id)
                if es_results:
                    backend = "elasticsearch"
                    results = es_results
            except Exception as exc:  # noqa: BLE001 - fall back to local
                log.warning("Elasticsearch match failed (%s); using local sample", exc)
        if not results:
            results = _local_match(vec, limit, self_id)

        span.set_attribute("match.backend", backend)
        span.set_attribute("match.results", len(results))
        return {"matches": results, "backend": backend, "dimensions": len(vec)}
