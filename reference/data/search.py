#!/usr/bin/env python3
"""
Hybrid search over the `talks` index, combining BM25 with vector/semantic
retrieval using Reciprocal Rank Fusion (RRF).

Detects the ingest mode from the index mapping (semantic_text vs dense_vector)
and builds the matching retriever:

  * Elasticsearch >= 8.16  -> retriever RRF API (standard + semantic|knn)
  * Elasticsearch 8.8-8.15 -> rank.rrf (query + knn) for dense_vector
  * semantic_text on 8.15  -> weighted bool fallback (no RRF in that release)

Environment:
  ES_URL       Elasticsearch endpoint            (default http://localhost:9200)
  ES_API_KEY   optional API key                  (leave unset when security off)

Usage:
  python3 search.py "ebpf and security" [--track Security] [--level Intermediate]
                  [--size 10] [--compare] [--no-vector]
"""

import argparse
import json
import os
from pathlib import Path

from elasticsearch import Elasticsearch

ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_API_KEY = os.environ.get("ES_API_KEY") or None

TALKS_INDEX = "talks"
SEMANTIC_FIELD = "content_semantic"
VECTOR_FIELD = "content_vector"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_embedder = None


def get_client():
    return Elasticsearch(ES_URL, api_key=ES_API_KEY, request_timeout=120)


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        print(f"[embed] loading model {EMBED_MODEL} ...")
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def version_tuple(info):
    raw = str(info.get("version", {}).get("number", "0.0.0"))
    parts = []
    for chunk in raw.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            parts.append(int(digits))
        if len(parts) == 2:
            break
    while len(parts) < 2:
        parts.append(0)
    return tuple(parts[:2])


def detect_mode(client):
    """Inspect the talks mapping to decide semantic_text vs dense_vector."""
    mapping = client.indices.get_mapping(index=TALKS_INDEX)
    props = mapping[TALKS_INDEX]["mappings"]["properties"]
    if SEMANTIC_FIELD in props:
        return "semantic_text"
    if VECTOR_FIELD in props:
        return "dense_vector"
    raise RuntimeError(f"neither {SEMANTIC_FIELD} nor {VECTOR_FIELD} found in "
                       f"'{TALKS_INDEX}' mapping — run ingest.py first")


def bm25_query(query):
    """BM25 over the text fields, boosting title/tags."""
    return {
        "multi_match": {
            "query": query,
            "type": "best_fields",
            "fields": [
                "title^4",
                "abstract^2",
                "tags^3",
                "speakers^1.5",
                "track^1",
            ],
        }
    }


def build_filter(track=None, level=None):
    must = []
    if track:
        must.append({"term": {"track": track}})
    if level:
        must.append({"term": {"level": level}})
    return {"bool": {"must": must}} if must else None


def hybrid_rrf_retrievers(client, query, mode, f, embed_vec):
    """Build the retrievers list for the retriever RRF API (ES >= 8.16)."""
    standard = {"standard": {"query": bm25_query(query)}}
    if f:
        standard["standard"]["filter"] = f

    if mode == "semantic_text":
        vec_retriever = {
            "semantic": {"field": SEMANTIC_FIELD, "query": query}
        }
    else:
        vec_retriever = {
            "knn": {
                "field": VECTOR_FIELD,
                "query_vector": embed_vec,
                "k": 100,
                "num_candidates": 200,
            }
        }
    if f:
        vec_retriever[list(vec_retriever.keys())[0]]["filter"] = f

    return [standard, vec_retriever]


def search_rrf_retriever(client, query, mode, f, embed_vec, size, ver):
    body = {
        "retriever": {
            "rrf": {
                "retrievers": hybrid_rrf_retrievers(client, query, mode, f, embed_vec),
                "rank_window_size": 100,
                "rank_constant": 60,
            }
        },
        "size": size,
    }
    return client.search(index=TALKS_INDEX, body=body)


def search_rank_rrf(client, query, f, embed_vec, size):
    """Fallback for ES 8.8-8.15 with dense_vector: query + knn + rank.rrf."""
    body = {
        "size": size,
        "query": bm25_query(query),
        "knn": {
            "field": VECTOR_FIELD,
            "query_vector": embed_vec,
            "k": 100,
            "num_candidates": 200,
        },
        "rank": {"rrf": {"window_size": 100, "rank_constant": 60}},
    }
    if f:
        body["query"] = {"bool": {"must": [bm25_query(query)], "filter": f}}
        body["knn"]["filter"] = f
    return client.search(index=TALKS_INDEX, body=body)


def search_weighted_bool(client, query, f, size):
    """Fallback for semantic_text on ES 8.15 (no RRF support yet)."""
    semantic = {"semantic": {"field": SEMANTIC_FIELD, "query": query, "boost": 1.0}}
    should = [bm25_query(query), semantic]
    body = {"size": size, "query": {"bool": {"should": should}}}
    if f:
        body["query"]["bool"]["filter"] = f
    return client.search(index=TALKS_INDEX, body=body)


def hybrid_search(client, query, mode, track=None, level=None, size=10):
    f = build_filter(track, level)
    ver = version_tuple(client.info())
    embed_vec = None
    if mode == "dense_vector":
        embed_vec = get_embedder().encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )[0].tolist()

    if ver >= (8, 16):
        return search_rrf_retriever(client, query, mode, f, embed_vec, size, ver)
    if mode == "dense_vector":
        return search_rank_rrf(client, query, f, embed_vec, size)
    return search_weighted_bool(client, query, f, size)


def bm25_only_search(client, query, track=None, level=None, size=10):
    f = build_filter(track, level)
    body = {"size": size, "query": bm25_query(query)}
    if f:
        body["query"] = {"bool": {"must": [bm25_query(query)], "filter": f}}
    return client.search(index=TALKS_INDEX, body=body)


def format_hit(hit):
    src = hit["_source"]
    time_str = src.get("start_time", "")
    return (f"{hit['_score']:>8.4f}  {src['id']}  [{src['track']}] "
            f"{src['title']}  ({time_str}, {src['room']}, {src['level']})\n"
            f"            speakers: {', '.join(src.get('speakers', []))}\n"
            f"            tags: {', '.join(src.get('tags', []))}")


def main():
    parser = argparse.ArgumentParser(description="Hybrid BM25+vector search with RRF")
    parser.add_argument("query", help="natural-language search query")
    parser.add_argument("--track", default=None)
    parser.add_argument("--level", default=None)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--compare", action="store_true",
                        help="also print BM25-only results for comparison")
    parser.add_argument("--no-vector", action="store_true",
                        help="run BM25-only instead of hybrid")
    args = parser.parse_args()

    client = get_client()
    try:
        client.info()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"cannot reach Elasticsearch at {ES_URL}: {exc}")

    if args.no_vector:
        resp = bm25_only_search(client, args.query, args.track, args.level, args.size)
        print(f"\n=== BM25-only results for '{args.query}' ===")
    else:
        mode = detect_mode(client)
        print(f"[mode] hybrid search using '{mode}' retrieval")
        resp = hybrid_search(client, args.query, mode, args.track, args.level, args.size)
        print(f"\n=== Hybrid (BM25 + {mode}) RRF results for '{args.query}' ===")

    hits = resp["hits"]["hits"]
    if not hits:
        print("  (no results)")
    for hit in hits:
        print("  " + format_hit(hit))

    if args.compare and not args.no_vector:
        bm = bm25_only_search(client, args.query, args.track, args.level, args.size)
        print(f"\n=== BM25-only results for '{args.query}' (comparison) ===")
        for hit in bm["hits"]["hits"]:
            print("  " + format_hit(hit))


if __name__ == "__main__":
    main()
