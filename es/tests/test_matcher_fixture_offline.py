"""The shared matcher fixture and our two-form cases, run without Elasticsearch (so CI covers them)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from confpilot_es.models import Glossary

from .offline_percolator import offline_percolate

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
SAMPLE_TERMS = Glossary.model_validate_json((FIXTURES / "glossary.sample.json").read_text(encoding="utf-8")).terms
MATCHER_CASES = json.loads((FIXTURES / "matcher_cases.json").read_text(encoding="utf-8"))
TWO_FORM_CASES = json.loads((Path(__file__).parent / "two_form_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", MATCHER_CASES, ids=[case["text"] for case in MATCHER_CASES])
def test_shared_matcher_case(case: dict) -> None:
    assert sorted(offline_percolate(case["text"], SAMPLE_TERMS)) == sorted(case["expect"])


@pytest.mark.parametrize("case", TWO_FORM_CASES, ids=[case["text"] for case in TWO_FORM_CASES])
def test_two_form_case(case: dict) -> None:
    assert offline_percolate(case["text"], SAMPLE_TERMS) == case["expect"]


def test_the_fixture_is_the_one_the_other_matchers_run() -> None:
    assert len(MATCHER_CASES) >= 23
