import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from confpilot import glossary as glossary_module
from confpilot.app import create_app
from confpilot.glossary import CONTENT_GLOSSARY, SAMPLE_GLOSSARY, load_glossary

SAMPLE = json.loads(SAMPLE_GLOSSARY.read_text(encoding="utf-8"))

TERM = {"id": "ebpf", "term": "eBPF", "level": 4, "simple_def": "Safe programs run in the kernel."}


def write_glossary(path: Path, version: str) -> Path:
    path.write_text(json.dumps({"version": version, "terms": [TERM]}), encoding="utf-8")
    return path


def test_get_glossary_matches_the_contract_sample(client: TestClient, spans) -> None:
    response = client.get("/api/glossary")

    assert response.status_code == 200
    assert response.json() == SAMPLE  # `say: null` stays, unset optional keys stay out
    span = next(s for s in spans.get_finished_spans() if s.name == "glossary.get")
    assert span.attributes["confpilot.glossary.version"] == SAMPLE["version"]


def test_the_real_glossary_is_the_default_and_is_served_as_version_and_terms(make_settings) -> None:
    real = json.loads(CONTENT_GLOSSARY.read_text(encoding="utf-8"))

    client = TestClient(create_app(make_settings(glossary_path=None)))

    body = client.get("/api/glossary").json()
    assert set(body) == {"version", "terms"}
    assert body["version"] == str(real["version"])
    assert body["terms"] == real["terms"]
    assert len(body["terms"]) >= 200


def test_glossary_path_wins(tmp_path: Path, make_settings) -> None:
    path = write_glossary(tmp_path / "g.json", "custom-1")

    client = TestClient(create_app(make_settings(glossary_path=path)))

    body = client.get("/api/glossary").json()
    assert body["version"] == "custom-1"
    assert body["terms"][0]["aliases"] == []
    assert "long_def" not in body["terms"][0]


def test_content_glossary_is_used_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        glossary_module, "CONTENT_GLOSSARY", write_glossary(tmp_path / "c.json", "content-1")
    )

    assert load_glossary().version == "content-1"


def test_missing_or_broken_glossary_falls_back_to_the_next_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    real_version = str(json.loads(CONTENT_GLOSSARY.read_text(encoding="utf-8"))["version"])

    assert load_glossary(tmp_path / "missing.json").version == real_version
    assert load_glossary(broken).version == real_version
    monkeypatch.setattr(glossary_module, "CONTENT_GLOSSARY", broken)
    assert load_glossary().version == SAMPLE["version"]


def test_no_glossary_anywhere_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(glossary_module, "CONTENT_GLOSSARY", tmp_path / "a.json")
    monkeypatch.setattr(glossary_module, "SAMPLE_GLOSSARY", tmp_path / "b.json")

    with pytest.raises(RuntimeError, match="No usable glossary"):
        load_glossary()
