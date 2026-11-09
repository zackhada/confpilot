#!/usr/bin/env python3
"""Shared helpers for the data agent: ES client, inference detection, embeddings."""

import os

from elasticsearch import Elasticsearch

TALKS_INDEX = "talks"
ATTENDEES_INDEX = "attendees"

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_client():
    """Build an ES client from ES_URL / ES_API_KEY env vars."""
    url = os.environ.get("ES_URL", "http://localhost:9200")
    api_key = os.environ.get("ES_API_KEY") or None
    if api_key:
        return Elasticsearch(url, api_key=api_key)
    return Elasticsearch(url)


def wait_for_es(client, timeout=120):
    """Block until Elasticsearch responds (handy after docker compose up)."""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if client.ping():
                return True
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"Elasticsearch not reachable within {timeout}s at "
                       f"{os.environ.get('ES_URL', 'http://localhost:9200')}")


def find_embedding_endpoint(client):
    """Return the inference_id of a text_embedding endpoint, or None.

    If an endpoint exists we use ES `semantic_text`; otherwise we fall back to
    sentence-transformers + `dense_vector`.
    """
    try:
        info = client.inference.get()
    except Exception:
        return None
    for ep in info.get("endpoints", []) or []:
        if ep.get("task_type") == "text_embedding":
            return ep.get("inference_id")
    return None


_embedder = None
_embedder_name = None


def load_embedder(model_name=None):
    """Lazily load a SentenceTransformer so semantic_text mode never needs it."""
    global _embedder, _embedder_name
    model_name = model_name or os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    if _embedder is not None and _embedder_name == model_name:
        return _embedder
    from sentence_transformers import SentenceTransformer

    _embedder = SentenceTransformer(model_name)
    _embedder_name = model_name
    return _embedder


def embed_texts(texts, model_name=None):
    """Embed a list of strings into normalized float vectors."""
    if isinstance(texts, str):
        texts = [texts]
    model = load_embedder(model_name)
    vectors = model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True)
    return [v.tolist() for v in vectors]


def embedding_dims(model_name=None):
    """Return the dimensionality of the embedding model."""
    model = load_embedder(model_name)
    return model.get_sentence_embedding_dimension()


def vector_field_info(client, index=TALKS_INDEX):
    """Inspect the live mapping and return (field_type, inference_id).

    field_type is 'semantic_text', 'dense_vector', or None.
    """
    mapping = client.indices.get_mapping(index=index)
    props = mapping[index]["mappings"]["properties"]
    field = props.get("embedding")
    if not field:
        return None, None
    return field.get("type"), field.get("inference_id")


def combined_talk_text(talk):
    return f"{talk['title']}\n{talk['abstract']}\n{' '.join(talk['tags'])}"


def combined_attendee_text(att):
    return (f"{att['name']} is a {att['role']} at {att['company']} "
            f"interested in {' '.join(att['interests'])}")
