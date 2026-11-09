"""A tiny stand-in for the percolator, so the shared matcher fixture also runs without a cluster.

It mirrors what the stored queries ask Elasticsearch to do (whole-word phrase match on either
normalized form, and the `intervals` rule for explicit context lists), then hands the candidates
to the real `resolve_matches`. The live tests check that Elasticsearch agrees.
"""

from __future__ import annotations

from confpilot_es.matching import CONTEXT_MAX_GAPS, Candidate, resolve_matches
from confpilot_es.models import Term
from confpilot_es.normalizer import variants
from confpilot_es.queries import percolator_doc


def _starts(tokens: list[str], phrase: str) -> list[tuple[int, int]]:
    words = phrase.split()
    return [
        (start, start + len(words))
        for start in range(len(tokens) - len(words) + 1)
        if tokens[start : start + len(words)] == words
    ]


def _stored_query_matches(doc: dict, tokens: list[str]) -> bool:
    spans = [span for phrase in doc["phrases"] for span in _starts(tokens, phrase)]
    if not (doc["ambiguous"] and doc["context"]):
        return bool(spans)
    context = [span for word in doc["context"] for form in variants(word) for span in _starts(tokens, form)]
    return any(
        max(c_start - end, start - c_end, 0) <= CONTEXT_MAX_GAPS for start, end in spans for c_start, c_end in context
    )


def offline_percolate(text: str, terms: list[Term]) -> list[str]:
    forms = [form.split() for form in variants(text)]
    candidates = []
    for term in terms:
        doc = percolator_doc(term)
        if any(_stored_query_matches(doc, tokens) for tokens in forms):
            candidates.append(
                Candidate(
                    term_id=term.id,
                    phrases=tuple(doc["phrases"]),
                    category=doc["category"],
                    ambiguous=doc["ambiguous"],
                    has_context=bool(doc["context"]),
                )
            )
    return resolve_matches(text, candidates)
