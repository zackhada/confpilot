from confpilot_es.matching import Candidate, resolve_matches
from confpilot_es.models import Term
from confpilot_es.queries import percolator_query, term_phrases

SEARCH = Candidate("search", ("search",), "data")
HYBRID = Candidate("hybrid-search", ("hybrid search",), "data")
POD = Candidate("pod", ("pod", "pods"), "cloud")
KNOWLEDGE_BASE = Candidate("knowledge-base", ("knowledge base",), "ai")
AGENT = Candidate("ai-agent", ("ai agent", "agent", "agents"), "ai", ambiguous=True)
TOKEN = Candidate("token", ("token", "tokens"), "ai", ambiguous=True)


def make_term(**overrides: object) -> Term:
    fields = {"id": "x", "term": "x", "aliases": [], "category": "cloud", "level": 2, "simple_def": "d"}
    return Term.model_validate({**fields, "prereqs": [], "source": "seed", **overrides})


def test_longest_term_first_drops_a_term_inside_a_longer_one() -> None:
    assert resolve_matches("pods use hybrid search", [SEARCH, HYBRID, POD]) == ["pod", "hybrid-search"]
    assert resolve_matches("search, then hybrid search", [SEARCH, HYBRID]) == ["search", "hybrid-search"]


def test_unlocatable_term_is_kept_only_when_unambiguous() -> None:
    cafe = Candidate("cafe", ("cafe",), "food")
    ghost = Candidate("ghost", ("ghost",), "food", ambiguous=True)
    assert resolve_matches("the café pod", [cafe, ghost, POD]) == ["pod", "cafe"]


def test_ambiguous_term_without_context_needs_a_same_category_neighbour() -> None:
    assert resolve_matches("a knowledge base the agent can use", [KNOWLEDGE_BASE, AGENT]) == [
        "knowledge-base",
        "ai-agent",
    ]
    assert resolve_matches("my travel agent booked the flights", [AGENT]) == []
    assert resolve_matches("the agent restarted the pod", [AGENT, POD]) == ["pod"]
    # Another ambiguous term is not context, and the neighbour must be within five words.
    assert resolve_matches("the agent spent a token", [AGENT, TOKEN]) == []
    far = "knowledge base one two three four five agent"
    assert resolve_matches(far, [KNOWLEDGE_BASE, AGENT]) == ["knowledge-base"]
    assert resolve_matches("agent a b c d knowledge base", [KNOWLEDGE_BASE, AGENT]) == ["ai-agent", "knowledge-base"]


def test_ambiguous_term_with_a_context_list_is_trusted_to_the_query() -> None:
    service = Candidate("service", ("service",), "cloud", ambiguous=True, has_context=True)
    assert resolve_matches("a kubernetes service", [service]) == ["service"]


def test_surface_forms_follow_the_glossary_builder() -> None:
    assert term_phrases(make_term(term="Service (Kubernetes)", aliases=["Service"])) == ["service"]
    assert term_phrases(make_term(term="Series A / B / C", aliases=["Series A", "seed round"])) == [
        "seed round",
        "series a",
    ]
    assert term_phrases(make_term(term="BM25", aliases=["best match 25"])) == ["best match 25", "best match25", "bm25"]


def test_percolator_query_shapes() -> None:
    plain = percolator_query(make_term(term="pod", aliases=["pods"]))
    assert plain["bool"]["should"] == [{"match_phrase": {"text": "pod"}}, {"match_phrase": {"text": "pods"}}]
    candidate = percolator_query(make_term(term="agent", ambiguous=True))
    assert candidate["bool"]["should"] == [{"match_phrase": {"text": "agent"}}]
    scoped = percolator_query(make_term(term="Service", ambiguous=True, context=["pod"]))
    assert scoped["intervals"]["text"]["all_of"]["max_gaps"] == 4
    assert percolator_query(make_term(term="A / B")) == {"match_none": {}}
