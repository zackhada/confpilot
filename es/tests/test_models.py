"""The Pydantic models must accept and produce exactly the shapes in contracts/types.ts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from confpilot_es import Glossary, Knowledge, KnowledgePatch, Recap, SearchHit

REPO = Path(__file__).resolve().parents[2]


def test_sample_and_real_glossaries_parse() -> None:
    sample = Glossary.model_validate_json((REPO / "contracts/fixtures/glossary.sample.json").read_text("utf-8"))
    real = Glossary.model_validate_json((REPO / "content/glossary.json").read_text("utf-8"))
    assert len(real.terms) == 200
    assert isinstance(real.version, str)  # content/glossary.json writes a number; the contract says string
    agent = next(term for term in sample.terms if term.id == "ai-agent")
    assert agent.say is None and agent.ambiguous is True and agent.context is None


def test_knowledge_starts_with_sm2_defaults() -> None:
    knowledge = Knowledge(user_id="u", term_id="rrf")
    assert json.loads(knowledge.model_dump_json()) == {
        "user_id": "u",
        "term_id": "rrf",
        "status": "unknown",
        "source": "tap",
        "encounters": 0,
        "ease": 2.5,
        "interval_days": 0.0,
        "reps": 0,
        "due_at": None,
        "learned": False,
    }


def test_knowledge_patch_is_partial_and_cannot_touch_the_ids() -> None:
    assert KnowledgePatch(status="known").model_dump(exclude_unset=True) == {"status": "known"}
    assert KnowledgePatch(due_at=None).model_dump(exclude_unset=True) == {"due_at": None}
    for bad in ({"user_id": "x"}, {"term_id": "x"}, {"status": "mastered"}, {"source": "guess"}):
        with pytest.raises(ValidationError):
            KnowledgePatch.model_validate(bad)


def test_search_hit_and_recap_use_the_contract_keys() -> None:
    hit = SearchHit(
        utterance_id="u1",
        speaker={"user_id": "user-zack", "name": "Zack"},
        spoken_at=1_794_000_000_000,
        text="we use RRF",
        highlight="we use <mark>RRF</mark>",
        term_ids=["rrf"],
    )
    assert set(hit.model_dump()) == {"utterance_id", "speaker", "spoken_at", "text", "highlight", "term_ids"}
    recap = Recap(room="slc1", new_term_count=1, heard=[{"term_id": "rrf", "count": 2}], learn_next=["rrf"])
    assert recap.model_dump()["heard"] == [{"term_id": "rrf", "count": 2}]
