#!/usr/bin/env python3
"""
Ingest the CloudNative Summit SLC 2026 dataset into Elasticsearch.

Creates a `talks` index with BM25 (text) fields plus a semantic field, and a
companion `attendees` index. Two semantic modes are supported and chosen
automatically at runtime:

  1. semantic_text  — used when a text_embedding / sparse_embedding inference
     endpoint is available on the cluster (Elasticsearch >= 8.15). Set
     ES_INFERENCE_ID to point at one, or pass --create-inference to try to
     deploy E5 / ELSER for you.
  2. dense_vector    — fallback: a dense_vector (384-dims) populated locally
     with sentence-transformers (all-MiniLM-L6-v2).

Environment:
  ES_URL       Elasticsearch endpoint            (default http://localhost:9200)
  ES_API_KEY   optional API key                  (leave unset when security off)
  ES_INFERENCE_ID  optional inference endpoint id to use for semantic_text

Usage:
  python3 ingest.py                  # talks + attendees
  python3 ingest.py --skip-attendees # talks only
  python3 ingest.py --create-inference  # try deploying E5/ELSER first
  python3 ingest.py --drop           # delete + recreate indexes first
"""

import argparse
import json
import os
import sys
from pathlib import Path

from elasticsearch import Elasticsearch, helpers

ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_API_KEY = os.environ.get("ES_API_KEY") or None
ES_INFERENCE_ID = os.environ.get("ES_INFERENCE_ID") or None

TALKS_INDEX = "talks"
ATTENDEES_INDEX = "attendees"

SEMANTIC_FIELD = "content_semantic"   # semantic_text mode
VECTOR_FIELD = "content_vector"       # dense_vector fallback mode
VECTOR_DIMS = 384
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Elasticsearch connection / version helpers
# ---------------------------------------------------------------------------
def get_client():
    return Elasticsearch(ES_URL, api_key=ES_API_KEY, request_timeout=120)


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


# ---------------------------------------------------------------------------
# Sentence-transformers fallback (lazy import so it is only required when used)
# ---------------------------------------------------------------------------
class Embedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        print(f"[embed] loading model {EMBED_MODEL} (first run downloads ~80MB) ...")
        self.model = SentenceTransformer(EMBED_MODEL)

    def embed(self, texts):
        vectors = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]


def combined_talk_text(talk):
    return f"{talk['title']}. {talk['abstract']}"


def combined_attendee_text(attendee):
    return " ".join(attendee["interests"])


# ---------------------------------------------------------------------------
# Inference endpoint discovery / creation
# ---------------------------------------------------------------------------
def _body(resp):
    """Normalise perform_request responses across elasticsearch-py versions."""
    if isinstance(resp, tuple):  # (status, headers, body) legacy style
        return resp[-1]
    return resp


def discover_inference_endpoint(client):
    """Return an existing text_embedding/sparse_embedding inference id, or None."""
    if ES_INFERENCE_ID:
        return ES_INFERENCE_ID
    try:
        resp = _body(client.perform_request("GET", "/_inference"))
        for ep in resp.get("endpoints", []):
            task = ep.get("task_type", "")
            if task in ("text_embedding", "sparse_embedding"):
                return ep.get("inference_id")
    except Exception as exc:  # noqa: BLE001
        print(f"[inference] could not list inference endpoints: {exc}")
    return None


def create_e5_endpoint(client):
    """Best-effort deployment of the multilingual E5 dense embedding model."""
    try:
        print("[inference] attempting to deploy multilingual E5 (dense) ...")
        client.perform_request(
            "PUT",
            "/_inference/text_embedding/cnh-e5",
            body={
                "service": "elasticsearch",
                "service_settings": {
                    "num_allocations": 1,
                    "num_threads": 1,
                    "model_id": ".multilingual-e5-small",
                },
            },
            request_timeout=600,
        )
        return "cnh-e5"
    except Exception as exc:  # noqa: BLE001
        print(f"[inference] E5 deployment failed: {exc}")
        return None


def create_elser_endpoint(client):
    """Best-effort deployment of the ELSER sparse embedding model."""
    try:
        print("[inference] attempting to deploy ELSER (sparse) ...")
        client.perform_request(
            "PUT",
            "/_inference/sparse_embedding/cnh-elser",
            body={"service": "elser",
                  "service_settings": {"num_allocations": 1, "num_threads": 1}},
            request_timeout=600,
        )
        return "cnh-elser"
    except Exception as exc:  # noqa: BLE001
        print(f"[inference] ELSER deployment failed: {exc}")
        return None


def resolve_mode(client, create_inference=False):
    """Return {"kind": "semantic_text"|"dense_vector", "inference_id": str|None}."""
    ver = version_tuple(client.info())
    supports_semantic_text = ver >= (8, 15)
    print(f"[info] Elasticsearch {'.'.join(map(str, ver))} at {ES_URL}")

    inference_id = discover_inference_endpoint(client)
    if inference_id:
        if not supports_semantic_text:
            print("[warn] inference endpoint found but this ES lacks semantic_text; "
                  "using dense_vector fallback.")
            return {"kind": "dense_vector", "inference_id": None}
        print(f"[mode] using native semantic_text via inference endpoint "
              f"'{inference_id}'")
        return {"kind": "semantic_text", "inference_id": inference_id}

    if create_inference and supports_semantic_text:
        inference_id = create_e5_endpoint(client) or create_elser_endpoint(client)
        if inference_id:
            print(f"[mode] using native semantic_text via inference endpoint "
                  f"'{inference_id}'")
            return {"kind": "semantic_text", "inference_id": inference_id}

    print("[mode] no inference endpoint available -> dense_vector fallback with "
          "sentence-transformers")
    return {"kind": "dense_vector", "inference_id": None}


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------
def base_talk_mappings():
    return {
        "id": {"type": "keyword"},
        "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
        "abstract": {"type": "text"},
        "speakers": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "track": {"type": "keyword"},
        "room": {"type": "keyword"},
        "start_time": {"type": "date"},
        "level": {"type": "keyword"},
        "tags": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
    }


def semantic_field(inference_id):
    return {"type": "semantic_text", "inference_id": inference_id}


def vector_field():
    return {
        "type": "dense_vector",
        "dims": VECTOR_DIMS,
        "index": True,
        "similarity": "cosine",
    }


def talks_mapping(mode):
    m = {"properties": base_talk_mappings()}
    if mode["kind"] == "semantic_text":
        m["properties"][SEMANTIC_FIELD] = semantic_field(mode["inference_id"])
    else:
        m["properties"][VECTOR_FIELD] = vector_field()
    return m


def attendees_mapping(mode):
    m = {"properties": {
        "id": {"type": "keyword"},
        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "role": {"type": "keyword"},
        "company": {"type": "keyword"},
        "interests": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
    }}
    if mode["kind"] == "semantic_text":
        m["properties"]["interests_semantic"] = semantic_field(mode["inference_id"])
    else:
        m["properties"]["interests_vector"] = vector_field()
    return m


# ---------------------------------------------------------------------------
# Index + bulk load
# ---------------------------------------------------------------------------
def ensure_index(client, index, mapping, drop=False):
    if drop:
        client.indices.delete(index=index, ignore=[400, 404])
        print(f"[index] dropped '{index}'")
    if not client.indices.exists(index=index):
        client.indices.create(index=index, mappings=mapping)
        print(f"[index] created '{index}'")
    else:
        print(f"[index] '{index}' already exists (skipping create)")


def build_talk_action(talk, mode, embedder):
    doc = dict(talk)
    doc["_index"] = TALKS_INDEX
    doc["_id"] = talk["id"]
    if mode["kind"] == "semantic_text":
        doc[SEMANTIC_FIELD] = combined_talk_text(talk)
    else:
        doc[VECTOR_FIELD] = embedder.embed([combined_talk_text(talk)])[0]
    return doc


def build_attendee_action(attendee, mode, embedder):
    doc = dict(attendee)
    doc["_index"] = ATTENDEES_INDEX
    doc["_id"] = attendee["id"]
    if mode["kind"] == "semantic_text":
        doc["interests_semantic"] = combined_attendee_text(attendee)
    else:
        doc["interests_vector"] = embedder.embed([combined_attendee_text(attendee)])[0]
    return doc


def bulk_index(client, actions, label):
    successes, errors = helpers.bulk(
        client, actions, chunk_size=100, raise_on_error=False, request_timeout=120
    )
    print(f"[bulk] {label}: {successes} indexed, {len(errors)} errors")
    for err in errors[:5]:
        print(f"  error: {err.get('index', err.get('create', {}))}")


def main():
    parser = argparse.ArgumentParser(description="Ingest talks + attendees into Elasticsearch")
    parser.add_argument("--drop", action="store_true", help="drop and recreate indexes")
    parser.add_argument("--skip-attendees", action="store_true", help="only index talks")
    parser.add_argument("--create-inference", action="store_true",
                        help="try to deploy E5/ELSER inference endpoint")
    args = parser.parse_args()

    talks_path = DATA_DIR / "talks.json"
    attendees_path = DATA_DIR / "attendees.json"
    if not talks_path.exists():
        sys.exit(f"missing {talks_path} — run 'python3 generate_data.py' first")

    talks = json.loads(talks_path.read_text())
    attendees = json.loads(attendees_path.read_text())

    client = get_client()
    try:
        client.info()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"cannot reach Elasticsearch at {ES_URL}: {exc}\n"
                 f"Tip: start it with `docker compose up -d`")

    mode = resolve_mode(client, create_inference=args.create_inference)
    embedder = Embedder() if mode["kind"] == "dense_vector" else None

    ensure_index(client, TALKS_INDEX, talks_mapping(mode), drop=args.drop)
    talk_actions = (build_talk_action(t, mode, embedder) for t in talks)
    bulk_index(client, talk_actions, "talks")

    if not args.skip_attendees:
        ensure_index(client, ATTENDEES_INDEX, attendees_mapping(mode), drop=args.drop)
        att_actions = (build_attendee_action(a, mode, embedder) for a in attendees)
        bulk_index(client, att_actions, "attendees")

    print("done.")


if __name__ == "__main__":
    main()
