"""Offline checks for connection settings and the mapping files."""

from __future__ import annotations

from pathlib import Path

import pytest

from confpilot_es.base import INDEX_NAMES, StoreBase, load_index_body
from confpilot_es.config import ConfigError, load_config

JINA = ".jina-embeddings-v5-text-small"


@pytest.fixture
def no_es_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ES_URL", "ES_API_KEY", "ENV_FILE"):
        monkeypatch.delenv(name, raising=False)


def test_config_reads_the_environment_first(monkeypatch: pytest.MonkeyPatch, no_es_env: None) -> None:
    monkeypatch.setenv("ES_URL", "https://example.es.io")
    monkeypatch.setenv("ES_API_KEY", "from-env")
    assert (load_config().url, load_config().api_key) == ("https://example.es.io", "from-env")


def test_config_falls_back_to_the_env_file(monkeypatch: pytest.MonkeyPatch, no_es_env: None, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nES_URL='https://file.es.io'\nexport ES_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("ENV_FILE", str(env_file))
    assert (load_config().url, load_config().api_key) == ("https://file.es.io", "from-file")


def test_config_fails_clearly_when_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch, no_es_env: None, tmp_path: Path
) -> None:
    with pytest.raises(ConfigError, match="ES_URL and ES_API_KEY"):
        load_config()
    monkeypatch.setenv("ENV_FILE", str(tmp_path / "missing.env"))
    with pytest.raises(ConfigError, match="does not exist"):
        load_config()


def test_every_index_has_a_mapping_file() -> None:
    bodies = {name: load_index_body(name) for name in INDEX_NAMES}
    assert all(body["mappings"]["properties"] for body in bodies.values())
    with pytest.raises(FileNotFoundError):
        load_index_body("nope")


def test_mappings_carry_the_search_features() -> None:
    terms = load_index_body("terms")["mappings"]["properties"]
    queries = load_index_body("term-queries")
    utterances = load_index_body("utterances")["mappings"]["properties"]
    assert terms["semantic_text"] == {"type": "semantic_text", "inference_id": JINA}
    assert utterances["semantic_text"] == {"type": "semantic_text", "inference_id": JINA}
    assert utterances["text"]["copy_to"] == "semantic_text"
    assert utterances["spoken_at"] == {"type": "date", "format": "epoch_millis"}
    assert queries["mappings"]["properties"]["query"] == {"type": "percolator"}
    analyzer = queries["settings"]["analysis"]["analyzer"]["confpilot_fold"]
    assert analyzer["filter"] == ["lowercase", "asciifolding"]
    assert queries["mappings"]["properties"]["text"]["analyzer"] == "confpilot_fold"


def test_index_names_are_prefixed_and_checked() -> None:
    store = StoreBase(client=None, prefix="confpilot-test-x-")  # type: ignore[arg-type]
    assert store.index("term-queries") == "confpilot-test-x-term-queries"
    with pytest.raises(ValueError, match="Unknown index"):
        store.index("users")
