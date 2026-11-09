"""Thin wrapper around the Elasticsearch client, created lazily from env."""
from __future__ import annotations

import logging

from . import config

log = logging.getLogger("confpilot.es")

_client = None
_resolved = False


def get_es():
    """Return a configured Elasticsearch client, or ``None`` when not configured."""
    global _client, _resolved
    if not _resolved:
        _resolved = True
        if not config.ES_URL:
            _client = None
            log.info("ES_URL not set; Elasticsearch features will degrade gracefully")
        else:
            try:
                from elasticsearch import Elasticsearch

                kwargs: dict = {
                    "hosts": [config.ES_URL],
                    "request_timeout": config.ES_TIMEOUT,
                }
                if config.ES_API_KEY:
                    kwargs["api_key"] = config.ES_API_KEY
                elif config.ES_USERNAME:
                    kwargs["basic_auth"] = (config.ES_USERNAME, config.ES_PASSWORD or "")
                _client = Elasticsearch(**kwargs)
            except Exception:  # pragma: no cover - defensive
                log.exception("Failed to create Elasticsearch client")
                _client = None
    return _client


def reset() -> None:
    """Reset the cached client (useful in tests)."""
    global _client, _resolved
    _client = None
    _resolved = False


def es_available() -> bool:
    """Cheap liveness check used by /healthz."""
    es = get_es()
    if es is None:
        return False
    try:
        return bool(es.ping())
    except Exception:
        return False
