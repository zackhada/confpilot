"""Search / RAG / match unit tests with mocked Elasticsearch + LLM."""
from __future__ import annotations

from confpilot.services.matching import cosine, interests_to_vector
from confpilot.services.search import rrf_merge


class FakeES:
    def __init__(self, hits=None):
        self.hits = hits or []
        self.calls = []

    def search(self, index=None, body=None, **kwargs):
        self.calls.append({"index": index, "body": body})
        return {"hits": {"hits": self.hits}}


TALK_1 = {
    "_id": "t1",
    "_score": 1.0,
    "_source": {
        "title": "eBPF for Security Engineers",
        "abstract": "How to use eBPF to observe and secure systems.",
        "speakers": ["Ada Lovelace"],
        "tags": ["ebpf", "security"],
        "room": "Grand Ballroom A",
        "track": "Security",
        "start_time": "10:00",
        "end_time": "10:45",
        "day": "Day 1",
    },
}
TALK_2 = {
    "_id": "t2",
    "_score": 0.9,
    "_source": {
        "title": "Kernel Networking with eBPF",
        "abstract": "Deep dive into eBPF programs in the kernel.",
        "speakers": ["Linus Torvalds"],
        "tags": ["ebpf", "kernel"],
        "room": "Breakout 2",
        "track": "Kernel",
        "start_time": "11:00",
        "end_time": "11:45",
        "day": "Day 1",
    },
}


def test_search_hybrid_bm25_only(client, monkeypatch):
    from confpilot.services import llm as llm_svc
    from confpilot.services import search as search_svc

    fake = FakeES([TALK_1, TALK_2])
    monkeypatch.setattr(search_svc, "get_es", lambda: fake)
    monkeypatch.setattr(llm_svc, "embed", lambda text: None)  # no vector model

    resp = client.get("/api/search", params={"q": "ebpf security"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert len(data["hits"]) == 2
    assert data["hits"][0]["title"] == "eBPF for Security Engineers"
    assert data["hits"][0]["matched_by"] == ["bm25"]


def test_search_vector_only_without_embedding(client, monkeypatch):
    from confpilot.services import llm as llm_svc
    from confpilot.services import search as search_svc

    fake = FakeES([])
    monkeypatch.setattr(search_svc, "get_es", lambda: fake)
    monkeypatch.setattr(llm_svc, "embed", lambda text: None)

    resp = client.get("/api/search", params={"q": "ebpf", "mode": "vector"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["hits"] == []


def test_rrf_merge_fuses_rankings():
    bm25 = {"a": (0, {}), "b": (1, {}), "c": (2, {})}
    knn = {"b": (0, {}), "c": (1, {}), "d": (2, {})}
    ranked = rrf_merge(bm25, knn, k=4)
    # "b" appears in both lists -> highest fused score
    assert ranked[0][0] == "b"
    assert {doc_id for doc_id, _ in ranked} == {"a", "b", "c", "d"}


def test_ask_rag(client, monkeypatch):
    from confpilot.services import llm as llm_svc
    from confpilot.services import search as search_svc

    monkeypatch.setattr(
        search_svc,
        "hybrid_search",
        lambda q, k=None, mode="hybrid": {
            "query": q,
            "hits": [
                {
                    "id": "t1",
                    "title": "eBPF for Security Engineers",
                    "abstract": "How to use eBPF to observe and secure systems.",
                    "speakers": ["Ada Lovelace"],
                    "tags": ["ebpf", "security"],
                    "room": "Grand Ballroom A",
                    "track": "Security",
                    "day": "Day 1",
                    "start_time": "10:00",
                    "score": 0.016,
                }
            ],
            "available": True,
        },
    )
    monkeypatch.setattr(
        llm_svc,
        "chat",
        lambda messages, **kw: (
            "eBPF is covered by 'eBPF for Security Engineers'.",
            {"prompt_tokens": 42, "completion_tokens": 8, "total_tokens": 50},
        ),
    )

    resp = client.post("/api/ask", json={"question": "which talks cover eBPF?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "eBPF" in data["answer"]
    assert data["sources"][0]["title"] == "eBPF for Security Engineers"
    assert data["usage"]["total_tokens"] == 50


def test_ask_llm_unavailable(client, monkeypatch):
    from confpilot.services import llm as llm_svc
    from confpilot.services import search as search_svc

    monkeypatch.setattr(search_svc, "hybrid_search", lambda q, k=None, mode="hybrid": {"hits": []})
    monkeypatch.setattr(llm_svc, "chat", lambda messages, **kw: (_ for _ in ()).throw(
        llm_svc.LLMUnavailable("LLM_BASE_URL is not configured")
    ))

    resp = client.post("/api/ask", json={"question": "hello"})
    assert resp.status_code == 503


def test_interests_to_vector_deterministic_and_similar():
    a = interests_to_vector(["ebpf", "security", "kubernetes"])
    b = interests_to_vector(["ebpf", "security", "kubernetes"])
    c = interests_to_vector(["baking", "gardening", "pottery"])
    assert a == b
    assert cosine(a, a) > 0.99  # normalized
    assert cosine(a, c) < cosine(a, b)


def test_match_returns_similar_people(client):
    resp = client.post("/api/match", json={"interests": ["ebpf", "security"], "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["backend"] == "local"
    names = [m["name"] for m in data["matches"]]
    assert len(names) == 3
    for expected in ("Ada Lovelace", "Linus Torvalds", "Radia Perlman"):
        assert expected in names
    # sorted by descending similarity
    sims = [m["similarity"] for m in data["matches"]]
    assert sims == sorted(sims, reverse=True)
