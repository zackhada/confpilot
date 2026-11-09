"""ConfPilot's Elasticsearch layer. Import the contract models from here."""

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
from confpilot_es.telemetry import EsStoreError

__all__ = [
    "ConfigError",
    "EsConfig",
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
