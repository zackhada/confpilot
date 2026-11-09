"""The shared matcher fixture, run against the live percolator (contracts/README.md section 6)."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import pytest

from confpilot_es import EsStore

from .conftest import MATCHER_CASES

pytestmark = pytest.mark.live

CASES = json.loads(MATCHER_CASES.read_text(encoding="utf-8"))
TWO_FORM_CASES = json.loads((Path(__file__).parent / "two_form_cases.json").read_text(encoding="utf-8"))
LATENCY_SAMPLES = 40


@pytest.mark.parametrize("case", CASES, ids=[case["text"] for case in CASES])
async def test_matcher_case(store: EsStore, case: dict) -> None:
    assert sorted(await store.percolate(case["text"])) == sorted(case["expect"])


@pytest.mark.parametrize("case", TWO_FORM_CASES, ids=[case["text"] for case in TWO_FORM_CASES])
async def test_two_form_case(store: EsStore, case: dict) -> None:
    assert await store.percolate(case["text"]) == case["expect"]


async def test_matches_come_back_in_spoken_order(store: EsStore) -> None:
    assert await store.percolate("we do SRE for Kubernetes clusters") == ["sre", "kubernetes", "cluster"]


async def test_ambiguous_term_needs_a_context_word_within_five_words(store: EsStore) -> None:
    assert await store.percolate("the pod red green blue pink service") == ["pod", "service"]
    assert await store.percolate("the pod red green blue pink grey service") == ["pod"]
    assert await store.percolate("ship it in a container") == []
    assert await store.percolate("a docker container") == ["container"]


async def test_version_numbers_do_not_hide_a_term(store: EsStore) -> None:
    assert await store.percolate("Kubernetes 1.30 is out") == ["kubernetes"]


async def test_blank_text_matches_nothing(store: EsStore) -> None:
    assert await store.percolate("  ...  ") == []


async def test_percolate_latency(store: EsStore, record_property: pytest.RecordProperty) -> None:
    texts = [case["text"] for case in CASES]
    await store.percolate(texts[0])  # warm the connection
    samples: list[float] = []
    for index in range(LATENCY_SAMPLES):
        started = time.perf_counter()
        await store.percolate(texts[index % len(texts)])
        samples.append((time.perf_counter() - started) * 1000)
    p50 = statistics.median(samples)
    p95 = statistics.quantiles(samples, n=20)[18]
    record_property("percolate_p50_ms", round(p50, 1))
    record_property("percolate_p95_ms", round(p95, 1))
    print(f"\npercolate latency over {LATENCY_SAMPLES} calls: p50={p50:.1f} ms p95={p95:.1f} ms")
    assert p95 < 2000
