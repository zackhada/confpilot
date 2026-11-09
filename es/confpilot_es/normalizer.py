"""Matcher normalizer: the Python twin of contracts/README.md section 6.

`base_tokens` only lowercases and strips punctuation. `normalize` applies every rule
(number words, spelled-out letters, letter and number runs). The percolator is fed both
forms, so an aggressive join such as "kubernetes 1.30" -> "kubernetes130" can add a match
but can never hide one.
"""

from __future__ import annotations

import re
import unicodedata

_UNITS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
_UNIT_VALUES = {word: value for value, word in enumerate(_UNITS)}
_TENS_VALUES = {word: (index + 2) * 10 for index, word in enumerate(_TENS)}

_APOSTROPHES = re.compile(r"['’`]")
_PUNCTUATION = re.compile(r"[^\w\s]|_")


def base_tokens(text: str) -> list[str]:
    """Lowercase, drop apostrophes, and turn all other punctuation into spaces."""
    lowered = unicodedata.normalize("NFKC", text).lower()
    return _PUNCTUATION.sub(" ", _APOSTROPHES.sub("", lowered)).split()


def _read_number_words(tokens: list[str]) -> list[str]:
    out: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        if token in _TENS_VALUES and 0 < _UNIT_VALUES.get(following, 0) < 10:
            out.append(str(_TENS_VALUES[token] + _UNIT_VALUES[following]))
            index += 2
            continue
        value = _TENS_VALUES.get(token, _UNIT_VALUES.get(token))
        out.append(token if value is None else str(value))
        index += 1
    return out


def _join_spelled_letters(tokens: list[str]) -> list[str]:
    """`r r f` -> `rrf`, `k 8 s` -> `k8s`: join runs of two or more one-character tokens."""
    out: list[str] = []
    run: list[str] = []
    for token in [*tokens, ""]:
        if len(token) == 1:
            run.append(token)
            continue
        if run:
            out.append("".join(run))
            run = []
        if token:
            out.append(token)
    return out


def _join_letter_number_runs(tokens: list[str]) -> list[str]:
    """`bm 25` -> `bm25`: glue a number onto the letters-only word before it."""
    out: list[str] = []
    for token in tokens:
        if out and token.isdigit() and out[-1].isalpha():
            out[-1] = out[-1] + token
        else:
            out.append(token)
    return out


def normalized_tokens(text: str) -> list[str]:
    tokens = _read_number_words(base_tokens(text))
    return _join_letter_number_runs(_join_spelled_letters(tokens))


def normalize(text: str) -> str:
    """Apply every section 6 rule: `and R.R.F. to rank` -> `and rrf to rank`."""
    return " ".join(normalized_tokens(text))


def variants(text: str) -> list[str]:
    """The distinct forms to match against: punctuation-stripped, then fully normalized."""
    forms = (" ".join(base_tokens(text)), normalize(text))
    return [form for form in dict.fromkeys(forms) if form]
