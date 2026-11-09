"""The normalizer and term matcher from contracts/README.md section 6.

The phone, the glossary checker and the percolator must agree with this, and
contracts/fixtures/matcher_cases.json is the shared test.

How it works: words are normalized into tokens, then every run of whole tokens is glued
together and looked up. Gluing is what makes "r r f", "bm 25", "bm twenty five" and
"crash loop back off" find RRF, BM25 and CrashLoopBackOff without a rule per spelling.
"""

import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from confpilot.models import Term

CONTEXT_WINDOW = 5
_SPACED = frozenset("-/‐‑‒–—")  # retrieval-augmented, CI/CD
_UNITS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
_TEENS = "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
_NUMBERS = (
    {w: n for n, w in enumerate(_UNITS)}
    | {w: n + 10 for n, w in enumerate(_TEENS)}
    | {w: (n + 2) * 10 for n, w in enumerate(_TENS)}
)


@dataclass(frozen=True, slots=True)
class Token:
    text: str
    first: int  # index of the first input word this token came from
    last: int


@dataclass(frozen=True, slots=True)
class Match:
    term_id: str
    first: int  # index of the first matched word
    last: int  # index of the last matched word


def _pieces(word: str) -> list[str]:
    """Hyphens and slashes become spaces; every other punctuation mark is deleted."""
    chars = [
        " " if c in _SPACED else c
        for c in unicodedata.normalize("NFKC", word).casefold()
        if c in _SPACED or c.isalnum()
    ]
    return "".join(chars).split()


def normalize(words: Sequence[str]) -> list[Token]:
    """Lowercase, strip punctuation, split hyphenated words and read number words."""
    raw = [Token(piece, i, i) for i, word in enumerate(words) for piece in _pieces(word)]
    tokens: list[Token] = []
    skip = False
    for token, following in zip(raw, [*raw[1:], None], strict=False):
        if skip:
            skip = False
            continue
        value = _NUMBERS.get(token.text)
        if value is None:
            tokens.append(token)
            continue
        unit = _NUMBERS.get(following.text) if following else None
        if value >= 20 and unit is not None and 1 <= unit <= 9:  # "twenty five" -> 25
            tokens.append(Token(str(value + unit), token.first, following.last))
            skip = True
        else:
            tokens.append(Token(str(value), token.first, token.last))
    return tokens


def _key(text: str) -> str:
    return "".join(t.text for t in normalize(text.split()))


Candidate = tuple[int, int, int, str]  # (-length of the glued form, first token, last token, id)


def _select(candidates: Iterable[Candidate], token_count: int) -> list[Candidate]:
    """Non-overlapping candidates, longest term first, then leftmost."""
    taken = [False] * token_count
    chosen: list[Candidate] = []
    for candidate in sorted(candidates):
        _, i, j, _ = candidate
        if not any(taken[i : j + 1]):
            taken[i : j + 1] = [True] * (j + 1 - i)
            chosen.append(candidate)
    return chosen


def _near(first: Token, last: Token, match_first: Token, match_last: Token) -> bool:
    """Is the span first..last within five spoken words of the match on either side?

    Distances are counted in input words, not tokens: "long-running" is one word although it
    becomes two tokens, and "twenty five" is two words although it becomes one.
    """
    return (
        last.last >= match_first.first - CONTEXT_WINDOW
        and first.first <= match_last.last + CONTEXT_WINDOW
    )


class Matcher:
    def __init__(self, terms: Iterable[Term]) -> None:
        self._forms: dict[str, str] = {}  # glued form -> term id
        self._context: dict[str, frozenset[str]] = {}  # ambiguous term with a context list
        self._needs_neighbour: dict[str, str] = {}  # ambiguous term without one -> category
        self._plain: dict[str, str] = {}  # term that is not ambiguous -> category
        for term in terms:
            for form in (term.term, *term.aliases):
                key = _key(form)
                if key:
                    self._forms.setdefault(key, term.id)
            context = frozenset(filter(None, map(_key, term.context or [])))
            if not term.ambiguous:
                self._plain[term.id] = term.category
            elif context:
                self._context[term.id] = context
            else:
                self._needs_neighbour[term.id] = term.category
        self._longest = max(map(len, self._forms), default=0)

    def _has_context_word(self, term_id: str, tokens: Sequence[Token], i: int, j: int) -> bool:
        context = self._context.get(term_id)
        if context is None:
            return True
        outside = (*tokens[:i], *tokens[j + 1 :])
        return any(t.text in context and _near(t, t, tokens[i], tokens[j]) for t in outside)

    def _is_lonely(
        self, candidate: Candidate, chosen: Iterable[Candidate], tokens: Sequence[Token]
    ) -> bool:
        """An ambiguous term without a context list needs a matched, plain, same-category
        term within five words on either side."""
        _, i, j, term_id = candidate
        category = self._needs_neighbour.get(term_id)
        if category is None:
            return False
        return not any(
            self._plain.get(other_id) == category
            and _near(tokens[other_i], tokens[other_j], tokens[i], tokens[j])
            for _, other_i, other_j, other_id in chosen
        )

    def match(self, words: Sequence[str]) -> list[Match]:
        """Terms found in ``words``, in spoken order, each with its first and last word index."""
        tokens = normalize(words)
        candidates: list[Candidate] = []
        for i in range(len(tokens)):
            key = ""
            for j in range(i, len(tokens)):
                key += tokens[j].text
                if len(key) > self._longest:
                    break
                term_id = self._forms.get(key)
                if term_id and self._has_context_word(term_id, tokens, i, j):
                    candidates.append((-len(key), i, j, term_id))

        # Dropping a lonely ambiguous match can free its words for a shorter term, so repeat.
        while True:
            chosen = _select(candidates, len(tokens))
            lonely = {c for c in chosen if self._is_lonely(c, chosen, tokens)}
            if not lonely:
                break
            candidates = [c for c in candidates if c not in lonely]
        return [
            Match(term_id, tokens[i].first, tokens[j].last)
            for i, j, term_id in sorted((i, j, term_id) for _, i, j, term_id in chosen)
        ]
