"""Live-cluster fixtures. Every test index is named confpilot-test-<run id>-* and deleted afterwards."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from confpilot_es import ConfigError, EsStore
from confpilot_es.bootstrap import bootstrap, read_glossary
from confpilot_es.config import load_config

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
SAMPLE_GLOSSARY = FIXTURES / "glossary.sample.json"
MATCHER_CASES = FIXTURES / "matcher_cases.json"


@pytest_asyncio.fixture(scope="session")
async def store() -> AsyncIterator[EsStore]:
    """A store on throwaway indices, bootstrapped with the sample glossary."""
    try:
        config = load_config()
    except ConfigError as exc:
        pytest.skip(f"live Elasticsearch not configured: {exc}")
    live = EsStore.from_env(prefix=f"confpilot-test-{uuid.uuid4().hex[:8]}-", refresh=True, config=config)
    try:
        await bootstrap(live, read_glossary(SAMPLE_GLOSSARY), recreate=True)
        yield live
    finally:
        await live.delete_indices()
        await live.close()
