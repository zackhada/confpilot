"""Resolve percolator hits into the final match list (contracts/README.md section 6).

Elasticsearch decides which terms are present as whole words, and enforces explicit `context`
lists inside the stored query. Two rules compare matches with each other, so they run here:
"longest term first", and the category rule for ambiguous terms that have no context list.
"""

from __future__ import annotations

from dataclasses import dataclass

from confpilot_es.normalizer import variants

# "within five words": at most four other words between the two.
CONTEXT_MAX_GAPS = 4


@dataclass(frozen=True)
class Candidate:
    """One percolator hit: a term whose stored query matched the utterance."""

    term_id: str
    phrases: tuple[str, ...]
    category: str = ""
    ambiguous: bool = False
    has_context: bool = False

    @property
    def needs_category_context(self) -> bool:
        return self.ambiguous and not self.has_context


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    candidate: Candidate

    def covers(self, other: _Span) -> bool:
        longer = self.end - self.start > other.end - other.start
        return longer and self.start <= other.start and other.end <= self.end

    def gap_to(self, other: _Span) -> int:
        return max(other.start - self.end, self.start - other.end, 0)


def _find_spans(tokens: list[str], candidates: list[Candidate]) -> list[_Span]:
    spans: list[_Span] = []
    for candidate in candidates:
        for phrase in candidate.phrases:
            words = phrase.split()
            for start in range(len(tokens) - len(words) + 1):
                if tokens[start : start + len(words)] == words:
                    spans.append(_Span(start, start + len(words), candidate))
    return spans


def _has_category_context(span: _Span, others: list[_Span]) -> bool:
    return any(
        not other.candidate.ambiguous
        and other.candidate.term_id != span.candidate.term_id
        and other.candidate.category == span.candidate.category
        and span.gap_to(other) <= CONTEXT_MAX_GAPS
        for other in others
    )


def resolve_matches(text: str, candidates: list[Candidate]) -> list[str]:
    """Return the matched term ids in order of first appearance.

    - A term is dropped when every place it occurs sits inside a longer phrase of another
      matched term (`search` inside `hybrid search`).
    - An ambiguous term with no context list is kept only when a matched, non-ambiguous term
      of the same category lies within five words on either side.
    - A term that cannot be located here (Elasticsearch folded an accent, say) is kept if it
      is unambiguous, because the percolator already matched it.
    """
    first_seen: dict[str, int] = {}
    located: set[str] = set()
    for form in variants(text):
        spans = _find_spans(form.split(), candidates)
        located.update(span.candidate.term_id for span in spans)
        longest = [span for span in spans if not any(other.covers(span) for other in spans)]
        for span in longest:
            candidate = span.candidate
            if candidate.needs_category_context and not _has_category_context(span, longest):
                continue
            first_seen[candidate.term_id] = min(span.start, first_seen.get(candidate.term_id, span.start))
    kept = [
        candidate.term_id
        for candidate in candidates
        if candidate.term_id in first_seen
        or (candidate.term_id not in located and not candidate.needs_category_context)
    ]
    return sorted(kept, key=lambda term_id: first_seen.get(term_id, len(text)))
