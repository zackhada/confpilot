from __future__ import annotations

import pytest

from confpilot_es import EsStore
from confpilot_es.base import INDEX_NAMES
from confpilot_es.bootstrap import bootstrap, read_glossary

from .conftest import SAMPLE_GLOSSARY

pytestmark = pytest.mark.live


async def test_bootstrap_creates_the_five_indices(store: EsStore) -> None:
    for name in INDEX_NAMES:
        assert await store.client.indices.exists(index=store.index(name)), name


async def test_glossary_round_trips_through_the_terms_index(store: EsStore) -> None:
    expected = read_glossary(SAMPLE_GLOSSARY)
    glossary = await store.get_glossary()
    assert glossary.version == expected.version
    assert glossary.terms == sorted(expected.terms, key=lambda term: term.id)


async def test_bootstrap_is_idempotent(store: EsStore) -> None:
    expected = read_glossary(SAMPLE_GLOSSARY)
    assert await store.ensure_indices() == []
    assert await bootstrap(store, expected) == len(expected.terms)
    queries = await store.client.count(index=store.index("term-queries"))
    assert queries["count"] == len(expected.terms)
