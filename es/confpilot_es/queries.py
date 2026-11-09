"""Pure builders for the Elasticsearch request bodies. No I/O, so they are easy to read and test."""

from __future__ import annotations

import re
from typing import Any

from confpilot_es.matching import CONTEXT_MAX_GAPS
from confpilot_es.models import Term
from confpilot_es.normalizer import variants

_PARENTHETICAL = re.compile(r"\s*\(.*?\)\s*")

Body = dict[str, Any]


def surface_forms(term: Term) -> list[str]:
    """The spoken forms of a term, as content/build_glossary.py defines them.

    "Service (Kubernetes)" is spoken as "Service"; "Series A / B / C" is a label, so only its
    aliases count.
    """
    display = _PARENTHETICAL.sub(" ", term.term).strip()
    spoken = [] if "/" in display else [display]
    return [form for form in (*spoken, *term.aliases) if form.strip()]


def term_phrases(term: Term) -> list[str]:
    """Every normalized spoken form of a term, longest first."""
    forms = {form for raw in surface_forms(term) for form in variants(raw)}
    return sorted(forms, key=lambda phrase: (-len(phrase.split()), phrase))


def _phrase_interval(phrase: str) -> Body:
    return {"match": {"query": phrase, "ordered": True, "max_gaps": 0}}


def percolator_query(term: Term) -> Body:
    """The stored query for one term: any of its phrases, as whole words.

    An ambiguous term with a `context` list only matches within five words of one of those
    words, expressed in the query itself with `intervals`. An ambiguous term without one is
    matched as a candidate here and confirmed against its neighbours in `matching.py`.
    """
    phrases = term_phrases(term)
    if not phrases:
        return {"match_none": {}}
    context = sorted({form for word in term.context or [] for form in variants(word)})
    if not (term.ambiguous and context):
        return {"bool": {"should": [{"match_phrase": {"text": p}} for p in phrases], "minimum_should_match": 1}}
    return {
        "intervals": {
            "text": {
                "all_of": {
                    "ordered": False,
                    "max_gaps": CONTEXT_MAX_GAPS,
                    "intervals": [
                        {"any_of": {"intervals": [_phrase_interval(p) for p in phrases]}},
                        {"any_of": {"intervals": [_phrase_interval(w) for w in context]}},
                    ],
                }
            }
        }
    }


def percolator_doc(term: Term) -> Body:
    return {
        "term_id": term.id,
        "term": term.term,
        "phrases": term_phrases(term),
        "category": term.category,
        "ambiguous": bool(term.ambiguous),
        "context": term.context or [],
        "source": term.source,
        "query": percolator_query(term),
    }


def term_doc(term: Term) -> Body:
    """The `terms` document: the contract fields plus the text that gets embedded."""
    definition = " ".join(part for part in (term.simple_def, term.long_def) if part)
    return {**term.model_dump(exclude_none=True), "semantic_text": f"{term.term}: {definition}"}
