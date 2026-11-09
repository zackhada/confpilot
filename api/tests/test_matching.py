import json
from pathlib import Path

import pytest

from confpilot.matching import Match, Matcher, normalize
from confpilot.models import Glossary, Term

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
CASES = json.loads((FIXTURES / "matcher_cases.json").read_text(encoding="utf-8"))
GLOSSARY = Glossary.model_validate_json(
    (FIXTURES / "glossary.sample.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def matcher() -> Matcher:
    return Matcher(GLOSSARY.terms)


@pytest.mark.parametrize("case", CASES, ids=[c["text"] for c in CASES])
def test_shared_matcher_cases(matcher: Matcher, case: dict) -> None:
    matches = matcher.match(case["text"].split())

    assert [m.term_id for m in matches] == case["expect"]


def texts(words: list[str]) -> list[str]:
    return [t.text for t in normalize(words)]


def test_normalize_lowercases_and_strips_punctuation() -> None:
    assert texts(["Hello,", "R.R.F.", "pod's", "?"]) == ["hello", "rrf", "pods"]


def test_only_hyphens_and_slashes_split_a_word() -> None:
    assert texts(["CI/CD", "on–call", "e.g.,x", "node_js", "a:b"]) == [
        "ci",
        "cd",
        "on",
        "call",
        "egx",
        "nodejs",
        "ab",
    ]


def test_normalize_splits_hyphens_and_keeps_the_word_index() -> None:
    tokens = normalize(["retrieval-augmented", "generation"])

    assert [(t.text, t.first, t.last) for t in tokens] == [
        ("retrieval", 0, 0),
        ("augmented", 0, 0),
        ("generation", 1, 1),
    ]


def test_normalize_reads_number_words() -> None:
    tokens = normalize(["bm", "twenty", "five", "and", "nine", "ninety"])

    assert [t.text for t in tokens] == ["bm", "25", "and", "9", "90"]
    assert (tokens[1].first, tokens[1].last) == (1, 2)


def test_match_returns_first_and_last_word_index(matcher: Matcher) -> None:
    words = "so a pod goes into crash loop back off again".split()

    assert matcher.match(words) == [Match("pod", 2, 2), Match("crashloopbackoff", 5, 8)]


def test_match_spans_spelled_out_number_words(matcher: Matcher) -> None:
    assert matcher.match("we use bm twenty five here".split()) == [Match("bm25", 2, 4)]


def test_longest_term_wins(matcher: Matcher) -> None:
    ids = [
        m.term_id for m in matcher.match("root cause analysis of the elastic search outage".split())
    ]

    assert ids == ["root-cause", "elasticsearch"]


def test_whole_words_only(matcher: Matcher) -> None:
    assert matcher.match("podcast ragged vectorized srely".split()) == []


def test_ambiguous_term_needs_context_within_five_words(matcher: Matcher) -> None:
    near = "the pod one two three four service".split()
    far = "the pod one two three four five service".split()

    assert "service" in [m.term_id for m in matcher.match(near)]
    assert "service" not in [m.term_id for m in matcher.match(far)]


def test_context_window_counts_spoken_words_not_tokens(matcher: Matcher) -> None:
    def ids(text: str) -> list[str]:
        return [m.term_id for m in matcher.match(text.split())]

    # A hyphenated word is one word, although it becomes two tokens.
    assert ids("the pod uses long-running self-healing service") == ["pod", "service"]
    assert ids("the pod a-b c-d e-f g-h service") == ["pod", "service"]  # five words away
    assert ids("the pod a-b c-d e-f g-h i-j service") == ["pod"]  # six words away
    # "twenty five" is two words, although it becomes one token.
    assert ids("the pod has twenty five replicas service") == ["pod", "service"]  # five away
    assert ids("the pod has twenty five replicas per service") == ["pod"]  # six away
    # The same holds for the same-category rule (agent has no context list).
    assert ids("a knowledge base that long-running self-healing agent") == [
        "knowledge-base",
        "ai-agent",
    ]


def test_empty_input(matcher: Matcher) -> None:
    assert matcher.match([]) == []
    assert matcher.match(["...", "-"]) == []


REPO = Path(__file__).resolve().parents[2]
MUST_CATCH_IDS = {"sre", "rag", "embedding", "bm25", "rrf"}


def test_the_demo_talk_track_finds_every_must_catch_term_in_the_real_glossary() -> None:
    glossary = Glossary.model_validate_json(
        (REPO / "content" / "glossary.json").read_text(encoding="utf-8")
    )
    talk = (REPO / "content" / "stt-fixtures" / "talk_track.txt").read_text(encoding="utf-8")

    found = {m.term_id for m in Matcher(glossary.terms).match(talk.split())}

    assert MUST_CATCH_IDS <= found


def test_an_ambiguous_term_without_a_context_list_needs_a_plain_same_category_neighbour() -> None:
    def term(term_id: str, category: str, **extra: object) -> Term:
        return Term(id=term_id, term=term_id, category=category, level=2, simple_def="x", **extra)

    matcher = Matcher(
        [
            term("agent", "ai", ambiguous=True),
            term("model", "ai", ambiguous=True),
            term("rag", "ai", ambiguous=False),
            term("pod", "cloud", ambiguous=False),
            term("travel agent", "ai", ambiguous=True),
        ]
    )

    def ids(text: str) -> list[str]:
        return [m.term_id for m in matcher.match(text.split())]

    assert ids("the agent uses rag") == ["agent", "rag"]
    assert ids("rag one two three four agent") == ["rag", "agent"]
    assert ids("rag one two three four five agent") == ["rag"]
    assert ids("the agent restarted the pod") == ["pod"]  # other category
    assert ids("the agent picks a model") == []  # ambiguous terms are not context for each other
    assert ids("my travel agent") == []  # dropping the long match does not revive "agent" alone
    assert ids("my travel agent likes rag") == ["travel agent", "rag"]
