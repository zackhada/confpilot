"""ConfPilot's Elasticsearch layer. Import `EsStore` and the contract models from here."""

from confpilot_es.config import ConfigError, EsConfig
from confpilot_es.models import (
    Glossary,
    HeardTerm,
    Knowledge,
    KnowledgePatch,
    Recap,
    SearchHit,
    Speaker,
    Term,
)
from confpilot_es.store import EsStore
from confpilot_es.telemetry import EsStoreError

__all__ = [
    "ConfigError",
    "EsConfig",
    "EsStore",
    "EsStoreError",
    "Glossary",
    "HeardTerm",
    "Knowledge",
    "KnowledgePatch",
    "Recap",
    "SearchHit",
    "Speaker",
    "Term",
]
