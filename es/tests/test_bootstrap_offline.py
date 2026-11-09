"""The bootstrap flow and CLI against a stub client."""

from __future__ import annotations

from pathlib import Path

import pytest

from confpilot_es import EsStore
from confpilot_es.bootstrap import bootstrap, main, read_glossary

from .stubs import StubClient

REPO = Path(__file__).resolve().parents[2]
SAMPLE_GLOSSARY = REPO / "contracts" / "fixtures" / "glossary.sample.json"
REAL_GLOSSARY = REPO / "content" / "glossary.json"


def test_read_glossary_accepts_the_real_file() -> None:
    glossary = read_glossary(REAL_GLOSSARY)
    assert len(glossary.terms) == 200
    assert isinstance(glossary.version, str) and glossary.version


async def test_bootstrap_creates_indices_loads_terms_and_prunes_stale_ones() -> None:
    glossary = read_glossary(SAMPLE_GLOSSARY)
    client = StubClient(exists=False, bulk={"errors": False, "items": []}, delete_by_query={"deleted": 0})
    store = EsStore(client, prefix="confpilot-test-stub-")  # type: ignore[arg-type]
    assert await bootstrap(store, glossary) == len(glossary.terms)
    assert len(client.calls_to("create")) == 5
    assert len(client.calls_to("bulk")[0]["operations"]) == 4 * len(glossary.terms)
    kept = client.calls_to("delete_by_query")[0]["query"]["bool"]["must_not"][0]["ids"]["values"]
    assert kept == [term.id for term in glossary.terms]
    assert not client.calls_to("delete")  # a plain run never drops an index


def test_cli_reports_a_missing_glossary(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    assert main(["--glossary", str(tmp_path / "nope.json")]) == 1
    assert "Bootstrap failed" in caplog.text


def test_cli_reports_missing_credentials(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    for name in ("ES_URL", "ES_API_KEY", "ENV_FILE"):
        monkeypatch.delenv(name, raising=False)
    assert main(["--glossary", str(SAMPLE_GLOSSARY)]) == 1
    assert "ES_URL and ES_API_KEY" in caplog.text
