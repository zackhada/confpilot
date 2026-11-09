"""Hybrid talk search: BM25 (lexical) + kNN (semantic) fused with RRF."""
from __future__ import annotations

import logging
import time

from opentelemetry import metrics, trace

from .. import config
from ..elasticsearch_client import get_es
from . import llm

log = logging.getLogger("confpilot.search")

tracer = trace.get_tracer("confpilot.search")
meter = metrics.get_meter("confpilot.search")

search_counter = meter.create_counter("confpilot.search.requests", "1", "search requests")
search_duration = meter.create_histogram("confpilot.search.duration", "s", "search latency")

SOURCE_FIELDS = [
    "title",
    "abstract",
    "speakers",
    "tags",
    "room",
    "track",
    "start_time",
    "end_time",
    "day",
]


def _bm25_body(query: str, k: int) -> dict:
    return {
        "size": k,
        "_source": SOURCE_FIELDS,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "abstract^2", "speakers^2", "tags^2", "track"],
                "type": "best_fields",
            }
        },
    }


def _knn_body(query_vector: list[float], k: int) -> dict:
    return {
        "size": k,
        "_source": SOURCE_FIELDS,
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": max(20, k * 5),
        },
    }


def _run_bm25(es, query: str, k: int, span) -> dict[str, tuple[int, dict]]:
    hits: dict[str, tuple[int, dict]] = {}
    resp = es.search(index=config.ES_INDEX_TALKS, body=_bm25_body(query, k))
    for rank, hit in enumerate(resp.get("hits", {}).get("hits", [])):
        hits[hit["_id"]] = (rank, hit)
    span.set_attribute("search.bm25.hits", len(hits))
    return hits


def _run_knn(es, query_vector: list[float], k: int, span) -> dict[str, tuple[int, dict]]:
    hits: dict[str, tuple[int, dict]] = {}
    resp = es.search(index=config.ES_INDEX_TALKS, body=_knn_body(query_vector, k))
    for rank, hit in enumerate(resp.get("hits", {}).get("hits", [])):
        hits[hit["_id"]] = (rank, hit)
    span.set_attribute("search.vector.hits", len(hits))
    return hits


def rrf_merge(
    bm25: dict[str, tuple[int, dict]],
    knn: dict[str, tuple[int, dict]],
    k: int,
    rrf_k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion over two ranked result sets."""
    scores: dict[str, float] = {}
    for doc_id, (rank, _) in bm25.items():
        scores[doc_id] = 1.0 / (rrf_k + rank + 1)
    for doc_id, (rank, _) in knn.items():
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]


def _format_hit(hit: dict, score: float, in_bm25: bool, in_knn: bool) -> dict:
    src = hit.get("_source", {}) or {}
    matched_by = []
    if in_bm25:
        matched_by.append("bm25")
    if in_knn:
        matched_by.append("vector")
    return {
        "id": hit.get("_id"),
        "score": round(score, 6),
        "matched_by": matched_by,
        "title": src.get("title"),
        "abstract": src.get("abstract"),
        "speakers": src.get("speakers") or [],
        "tags": src.get("tags") or [],
        "room": src.get("room"),
        "track": src.get("track"),
        "start_time": src.get("start_time"),
        "end_time": src.get("end_time"),
        "day": src.get("day"),
    }


def _empty(query: str, mode: str, start: float, reason: str) -> dict:
    return {
        "query": query,
        "mode": mode,
        "hits": [],
        "took_ms": round((time.perf_counter() - start) * 1000, 2),
        "available": False,
        "note": reason,
    }


def hybrid_search(query: str, k: int | None = None, mode: str = "hybrid") -> dict:
    """Run hybrid (BM25 + vector) search against the ``talks`` index.

    ``mode`` is one of ``hybrid`` (default), ``bm25``, or ``vector``.
    """
    k = k or config.SEARCH_DEFAULT_K
    start = time.perf_counter()
    search_counter.add(1, {"mode": mode})

    with tracer.start_as_current_span("search") as span:
        span.set_attributes(
            {"search.query": query, "search.mode": mode, "search.k": k}
        )
        es = get_es()
        if es is None:
            span.set_attribute("search.available", False)
            return _empty(query, mode, start, "Elasticsearch is not configured (set ES_URL/ES_API_KEY)")

        bm25: dict[str, tuple[int, dict]] = {}
        knn: dict[str, tuple[int, dict]] = {}

        if mode in ("hybrid", "bm25"):
            try:
                bm25 = _run_bm25(es, query, k, span)
            except Exception as exc:  # noqa: BLE001 - degrade gracefully
                log.warning("BM25 search failed: %s", exc)
                span.set_attribute("search.bm25.error", str(exc)[:200])

        if mode in ("hybrid", "vector"):
            query_vector = llm.embed(query)
            if query_vector is not None:
                try:
                    knn = _run_knn(es, query_vector, k, span)
                except Exception as exc:  # noqa: BLE001 - degrade to BM25
                    log.warning("kNN search failed: %s", exc)
                    span.set_attribute("search.vector.error", str(exc)[:200])
            else:
                span.set_attribute("search.embedding_available", False)
                if mode == "vector":
                    return _empty(query, mode, start, "No embedding model available for vector-only search")

        ranked = rrf_merge(bm25, knn, k)
        hits = [
            _format_hit(bm25[sid][1] if sid in bm25 else knn[sid][1], score, sid in bm25, sid in knn)
            for sid, score in ranked
        ]

        span.set_attribute("search.results", len(hits))
        duration = time.perf_counter() - start
        search_duration.record(duration, {"mode": mode})
        return {
            "query": query,
            "mode": mode,
            "hits": hits,
            "took_ms": round(duration * 1000, 2),
            "available": True,
        }
