import pytest
from fastapi.testclient import TestClient
from helpers import bearer, room_url

from confpilot.models import Glossary, Knowledge, Term
from confpilot.routes.knowledge import build_recap


def say(socket, utterance_id: str, text: str) -> None:
    socket.send_json(
        {
            "type": "transcript",
            "utterance_id": utterance_id,
            "seq": 1,
            "is_final": True,
            "text": text,
            "words": [],
            "started_at": 1731177600000,
        }
    )


@pytest.fixture(autouse=True)
def signed_in_as_ana(client: TestClient) -> None:
    client.headers.update(bearer(client, "u-ana"))


@pytest.fixture
def talked(client: TestClient) -> TestClient:
    """A room where Ana said three things."""
    with client.websocket_connect(room_url(client, "u-ana", "Ana")) as ana:
        say(ana, "u1", "we use RAG with <b> embeddings </b>")
        say(ana, "u2", "RAG needs vectors and embeddings")
        say(ana, "u3", "RAG again, plus lunch")
        ana.send_json({"type": "time.ping", "t0": 0})
        while ana.receive_json()["type"] != "time.pong":
            pass
    return client


def test_knowledge_starts_empty_then_put_creates_and_merges(client: TestClient, spans) -> None:
    assert client.get("/api/users/u-ana/knowledge").json() == {"items": []}

    created = client.put("/api/users/u-ana/knowledge/rag", json={"status": "learning"})
    merged = client.put(
        "/api/users/u-ana/knowledge/rag",
        json={"interval_days": 7, "reps": 2, "due_at": 1731782400000, "user_id": "ignored"},
    )

    assert created.json() == {
        "user_id": "u-ana",
        "term_id": "rag",
        "status": "learning",
        "source": "tap",
        "encounters": 0,
        "ease": 2.5,
        "interval_days": 0,
        "reps": 0,
        "due_at": None,
        "learned": False,
    }
    assert merged.json() | {"interval_days": 7.0} == created.json() | {
        "interval_days": 7.0,
        "reps": 2,
        "due_at": 1731782400000,
        "learned": True,
    }
    assert client.get("/api/users/u-ana/knowledge").json() == {"items": [merged.json()]}
    assert {"knowledge.list", "knowledge.put"} <= {s.name for s in spans.get_finished_spans()}


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/users/bad%20id!/knowledge", None),
        ("put", "/api/users/u-ana/knowledge/" + "x" * 65, {}),
        ("put", "/api/users/u-ana/knowledge/rag", {"status": "mastered"}),
        ("put", "/api/users/u-ana/knowledge/rag", {"ease": -1}),
        ("get", "/api/rooms/bad%20room/recap", None),
        ("get", "/api/rooms/slc1/recap?user_id=a.b", None),
        ("get", "/api/search", None),
        ("get", "/api/search?q=", None),
        ("get", "/api/search?q=" + "x" * 201, None),
        ("get", "/api/search?q=rag&room=bad%20room", None),
        ("get", "/api/search?q=rag&room=slc1&limit=500", None),
        ("get", "/api/search?q=rag", None),
    ],
)
def test_bad_input_is_a_422(client: TestClient, method: str, path: str, body: dict | None) -> None:
    assert client.request(method, path, json=body).status_code == 422


def test_recap_counts_what_was_heard_and_personalizes(talked: TestClient) -> None:
    everyone = talked.get("/api/rooms/slc1/recap").json()
    talked.put("/api/users/u-ana/knowledge/vector", json={"status": "known"})
    ana = talked.get("/api/rooms/slc1/recap?user_id=u-ana").json()

    assert everyone == {
        "room": "slc1",
        "new_term_count": 3,
        "heard": [
            {"term_id": "rag", "count": 3},
            {"term_id": "embedding", "count": 2},
            {"term_id": "vector", "count": 1},
        ],
        # Nothing is known, so only vector (no prerequisites) is on the frontier.
        "learn_next": ["vector", "rag", "embedding"],
    }
    assert (ana["new_term_count"], ana["learn_next"]) == (2, ["embedding", "rag"])


def test_recap_and_search_are_for_room_members_only(talked: TestClient) -> None:
    ben = bearer(talked, "u-ben")  # has a session, never joined slc1

    assert talked.get("/api/rooms/slc1/recap", headers=ben).status_code == 403
    assert talked.get("/api/search?q=rag&room=slc1", headers=ben).status_code == 403
    assert talked.get("/api/rooms/other/recap").status_code == 403  # Ana never joined "other"
    assert talked.get("/api/search?q=rag&room=other").status_code == 403
    # Ana left the room when her socket closed; a past member can still read it.
    assert talked.get("/api/rooms/slc1/recap").status_code == 200


def test_recap_and_search_reject_someone_elses_user_id(talked: TestClient) -> None:
    assert talked.get("/api/rooms/slc1/recap?user_id=u-ben").status_code == 403
    assert talked.get("/api/search?q=rag&room=slc1&user_id=u-ben").status_code == 403


def test_build_recap_treats_learned_as_known() -> None:
    glossary = Glossary(
        version="t", terms=[Term(id="b", term="B", level=1, simple_def="x", prereqs=["a"])]
    )
    learned = Knowledge(user_id="u", term_id="a", status="learning", learned=True)

    recap = build_recap("r", {"a": 5, "b": 1, "c": 1}, [learned], glossary)

    assert (recap.new_term_count, recap.learn_next) == (2, ["b", "c"])


def test_search_finds_utterances_with_escaped_highlights(talked: TestClient, spans) -> None:
    hits = talked.get("/api/search?q=EMBEDDINGS&room=slc1&user_id=u-ana").json()["hits"]

    assert [h["utterance_id"] for h in hits] == ["u1", "u2"]
    assert hits[0] == {
        "utterance_id": "u1",
        "speaker": {"user_id": "u-ana", "name": "Ana"},
        "spoken_at": 1731177600000,
        "text": "we use RAG with <b> embeddings </b>",
        "highlight": "we use RAG with &lt;b&gt; <mark>embeddings</mark> &lt;/b&gt;",
        "term_ids": ["rag", "embedding"],
    }
    assert len(talked.get("/api/search?q=rag&room=slc1&limit=2").json()["hits"]) == 2
    span = next(s for s in spans.get_finished_spans() if s.name == "search")
    assert span.attributes["confpilot.search.hit_count"] == 2
