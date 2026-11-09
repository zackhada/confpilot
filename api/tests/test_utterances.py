from fastapi.testclient import TestClient

from confpilot.utterances import RecentFinals, is_duplicate

ANA_URL = "/ws/rooms/slc1?user_id=u-ana&name=Ana&role=speaker"
BEN_URL = "/ws/rooms/slc1?user_id=u-ben&name=Ben&role=speaker"
SENTENCE = "we use RAG and BM 25 on Kubernetes for search"
T0 = 1731177600000


def final(utterance_id: str, text: str, is_final: bool = True, started_at: int = T0) -> dict:
    words = [
        {"w": w, "start_ms": i * 100, "end_ms": i * 100 + 90} for i, w in enumerate(text.split())
    ]
    return {
        "type": "transcript",
        "utterance_id": utterance_id,
        "seq": 1,
        "is_final": is_final,
        "text": text,
        "words": words,
        "started_at": started_at,
    }


def settle(socket) -> list[dict]:
    """A ping round trip: by the time the pong is back, earlier events are handled.
    Returns what arrived on this socket before the pong."""
    socket.send_json({"type": "time.ping", "t0": 0})
    seen = []
    while (event := socket.receive_json())["type"] != "time.pong":
        seen.append(event)
    return seen


def stored(client: TestClient) -> dict[tuple[str, str], str]:
    utterances = client.app.state.store._utterances.get("slc1", {})
    return {key: utterance.text for key, utterance in utterances.items()}


def test_duplicate_needs_four_words_each_and_80_percent_of_the_longer() -> None:
    ten = "a b c d e f g h i j".split()

    assert is_duplicate(ten, ten)
    assert is_duplicate(ten, ten[:8])  # 8 of 10 in common
    assert not is_duplicate(ten, ten[:7])  # 7 of 10
    assert not is_duplicate(ten, ["a"])  # a tiny final never matches a long one
    assert not is_duplicate(["a", "b", "c"], ["a", "b", "c"])  # under four words
    assert not is_duplicate(
        ["a", "a", "a", "a", "a"], ["a", "b", "c", "d", "e"]
    )  # repeats count once


def test_recent_finals_keep_the_first_arrival_and_drop_a_later_copy() -> None:
    recent = RecentFinals()
    words = SENTENCE.split()

    assert recent.admit("slc1", "u-ana", words, now=10.0)
    assert not recent.admit("slc1", "u-ben", ["We", "use", "rag,", *words[3:]], now=11.0)
    assert recent.admit("slc1", "u-ana", words, now=11.5)  # a speaker may repeat themselves
    assert recent.admit("other", "u-ben", words, now=11.5)  # rooms are separate
    assert recent.admit("slc1", "u-ben", "something else entirely was said".split(), now=12.0)
    assert recent.admit("slc1", "u-ben", words, now=14.6)  # more than 3 s after Ana's last
    assert not recent.admit("slc1", "u-ben", ["...", "?"], now=20.0)  # nothing to store
    assert "slc1" not in recent._rooms  # everything aged out, so the room is forgotten


def test_forget_removes_only_the_exact_admission() -> None:
    recent = RecentFinals()
    words = SENTENCE.split()

    assert recent.admit("slc1", "u-ana", words, now=10.0)
    assert recent.admit("slc1", "u-ana", words, now=11.0)

    recent.forget("slc1", "u-ana", words, at=10.0)

    assert not recent.admit("slc1", "u-ben", words, now=11.5)


def test_finals_are_matched_and_stored_once(client: TestClient, spans) -> None:
    with client.websocket_connect(ANA_URL) as ana, client.websocket_connect(BEN_URL) as ben:
        ana.send_json(final("utt-a1", SENTENCE, is_final=False))
        ana.send_json(final("utt-a1", SENTENCE))
        settle(ana)
        ben.send_json(final("utt-b1", SENTENCE.lower()))  # Ben's phone heard Ana too
        ben.send_json(final("utt-b2", "the pod is in crash loop back off"))
        settle(ben)
        relayed_to_ana = [e.get("utterance_id") for e in settle(ana)]

    assert list(stored(client)) == [("u-ana", "utt-a1"), ("u-ben", "utt-b2")]
    assert "utt-b1" in relayed_to_ana  # the dropped final was still relayed
    utterances = client.app.state.store._utterances["slc1"]
    assert utterances[("u-ana", "utt-a1")].term_ids == ["rag", "bm25", "kubernetes"]
    assert utterances[("u-ana", "utt-a1")].speaker.name == "Ana"
    assert utterances[("u-ana", "utt-a1")].spoken_at == T0
    assert utterances[("u-ben", "utt-b2")].term_ids == ["pod", "crashloopbackoff"]
    session = client.app.state.store._sessions["slc1"]
    assert [s.user_id for s in session.speakers] == ["u-ana", "u-ben"]
    relays = [s for s in spans.get_finished_spans() if s.name == "transcript.relay"]
    assert [s.attributes.get("confpilot.utterance.duplicate") for s in relays] == [
        None,
        False,
        True,
        False,
    ]
    assert len([s for s in spans.get_finished_spans() if s.name == "utterance.store"]) == 2


def test_dropped_store_work_does_not_suppress_another_speakers_copy(
    client: TestClient, spans, monkeypatch
) -> None:
    monkeypatch.setattr("confpilot.routes.ws.MAX_BACKGROUND_TASKS", 0)
    with client.websocket_connect(ANA_URL) as ana, client.websocket_connect(BEN_URL) as ben:
        ana.send_json(final("utt-a1", SENTENCE))
        settle(ana)
        ben.send_json(final("utt-b1", SENTENCE))
        settle(ben)

    assert stored(client) == {}
    assert client.app.state.recent_finals._rooms == {}
    relays = [s for s in spans.get_finished_spans() if s.name == "transcript.relay"]
    assert [s.attributes["confpilot.utterance.duplicate"] for s in relays] == [False, False]
    assert [s.attributes["confpilot.utterance.store_dropped"] for s in relays] == [True, True]


def test_a_failed_store_releases_the_final_so_the_other_copy_is_kept(
    client: TestClient, monkeypatch
) -> None:
    store = client.app.state.store
    real_add = store.add_utterance
    calls = []

    async def fail_once(utterance) -> None:
        calls.append(utterance.utterance_id)
        if len(calls) == 1:
            raise RuntimeError("store is down")
        await real_add(utterance)

    monkeypatch.setattr(store, "add_utterance", fail_once)
    with client.websocket_connect(ANA_URL) as ana, client.websocket_connect(BEN_URL) as ben:
        ana.send_json(final("utt-a1", SENTENCE))  # storing this one fails
        settle(ana)
        ben.send_json(final("utt-b1", SENTENCE))  # the same sentence from the other phone
        settle(ben)

    assert calls == ["utt-a1", "utt-b1"]
    assert stored(client) == {("u-ben", "utt-b1"): SENTENCE}


def test_a_one_word_final_cannot_suppress_or_replace_a_long_one(client: TestClient) -> None:
    with client.websocket_connect(ANA_URL) as ana, client.websocket_connect(BEN_URL) as ben:
        ben.send_json(final("utt-b1", "search"))  # arrives first, shares a word
        settle(ben)
        ana.send_json(final("utt-a1", SENTENCE))
        settle(ana)
        ben.send_json(final("utt-b2", "Kubernetes"))  # arrives after, shares a word
        settle(ben)

    assert stored(client) == {
        ("u-ben", "utt-b1"): "search",
        ("u-ana", "utt-a1"): SENTENCE,
        ("u-ben", "utt-b2"): "Kubernetes",
    }


def test_an_early_started_at_cannot_remove_a_stored_final(client: TestClient) -> None:
    with client.websocket_connect(ANA_URL) as ana, client.websocket_connect(BEN_URL) as ben:
        ana.send_json(final("utt-a1", SENTENCE))
        settle(ana)
        ben.send_json(final("utt-b1", SENTENCE, started_at=T0 - 60_000))  # claims to be earlier
        ben.send_json(final("utt-a1", SENTENCE, started_at=0))  # and reuses Ana's utterance id
        settle(ben)

    assert stored(client) == {("u-ana", "utt-a1"): SENTENCE}
    assert client.app.state.store._utterances["slc1"][("u-ana", "utt-a1")].spoken_at == T0
