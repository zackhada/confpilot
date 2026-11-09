"""Shared plumbing for the store mixins: the client, index names and mapping files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from elasticsearch import AsyncElasticsearch

from confpilot_es.config import DEFAULT_PREFIX

INDEX_NAMES = ("terms", "term-queries", "utterances", "user-knowledge", "sessions")

_PACKAGE_DIR = Path(__file__).resolve().parent
# Installed wheels carry the mappings inside the package; a source checkout keeps them in es/mappings.
_MAPPING_DIRS = (_PACKAGE_DIR / "mappings", _PACKAGE_DIR.parent / "mappings")


def load_index_body(name: str) -> dict[str, Any]:
    """Return the `{settings, mappings}` body for one of INDEX_NAMES."""
    for directory in _MAPPING_DIRS:
        path = directory / f"{name}.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"No mapping file for index '{name}' in {[str(d) for d in _MAPPING_DIRS]}")


class StoreBase:
    """Holds the async client and resolves prefixed index names."""

    def __init__(self, client: AsyncElasticsearch, prefix: str = DEFAULT_PREFIX, refresh: bool = False) -> None:
        self.client = client
        self.prefix = prefix
        # Utterance writes refresh only when asked: tests need read-your-writes, the live path does not.
        self.refresh = refresh

    def index(self, name: str) -> str:
        if name not in INDEX_NAMES:
            raise ValueError(f"Unknown index '{name}'. Expected one of {INDEX_NAMES}.")
        return f"{self.prefix}{name}"

    async def close(self) -> None:
        await self.client.close()
