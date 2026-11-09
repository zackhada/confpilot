"""Matcher normalizer: the Python twin of contracts/README.md section 6.

`base_tokens` lowercases, turns hyphens and slashes into spaces and deletes other punctuation.
`normalize` then applies the joining rules (number words, spelled-out letters, letter and
number runs). The percolator is fed every form from `variants`, so an aggressive join such as
"kubernetes 1.30" -> "kubernetes130" can add a match but can never hide one.
"""

from __future__ import annotations

import re
import unicodedata

_UNITS = (  # noqa: SIM905 - one readable line beats twenty
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()  # noqa: SIM905
_UNIT_VALUES = {word: value for value, word in enumerate(_UNITS)}
_TENS_VALUES = {word: (index + 2) * 10 for index, word in enumerate(_TENS)}

_DASHES = "".join(chr(code) for code in range(0x2010, 0x2016))  # Unicode hyphens and dashes
_WORD_BREAKS = re.compile(rf"[-/\\{_DASHES}]")
_PUNCTUATION = re.compile(r"[^\w\s]|_")
_ARTICLES = frozenset({"a", "i"})  # one-letter words that are not always spelled-out letters


def base_tokens(text: str) -> list[str]:
    """Lowercase, turn hyphens and slashes into spaces, and delete every other punctuation mark."""
    lowered = unicodedata.normalize("NFKC", text).lower()
    return _PUNCTUATION.sub("", _WORD_BREAKS.sub(" ", lowered)).split()


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


def _join_spelled_letters(tokens: list[str], split_article: bool = False) -> list[str]:
    """`r r f` -> `rrf`, `k 8 s` -> `k8s`: join runs of two or more one-character tokens.

    With `split_article`, a leading "a" or "i" is read as a word and left out of a longer run:
    `a k 8 s` -> `a k8s` rather than `ak8s`.
    """
    out: list[str] = []
    run: list[str] = []
    for token in [*tokens, ""]:
        if len(token) == 1:
            run.append(token)
            continue
        if split_article and len(run) > 2 and run[0] in _ARTICLES:
            out.append(run.pop(0))
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


def normalized_tokens(text: str, split_article: bool = False) -> list[str]:
    tokens = _read_number_words(base_tokens(text))
    return _join_letter_number_runs(_join_spelled_letters(tokens, split_article))


def normalize(text: str) -> str:
    """Apply every section 6 rule: `and R.R.F. to rank` -> `and rrf to rank`."""
    return " ".join(normalized_tokens(text))


def variants(text: str) -> list[str]:
    """The distinct forms to match against.

    Punctuation-stripped, fully normalized, and normalized with a leading "a" or "i" kept out
    of a spelled-out run (`a p i` must reach `api`, and `a k 8 s` must reach `k8s`).
    """
    forms = (
        " ".join(base_tokens(text)),
        normalize(text),
        " ".join(normalized_tokens(text, split_article=True)),
    )
    return [form for form in dict.fromkeys(forms) if form]
