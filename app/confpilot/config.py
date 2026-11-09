"""Runtime configuration, read from environment variables."""
from __future__ import annotations

import os


def _get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _int(name: str, default: int) -> int:
    try:
        return int(_get(name, str(default)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(_get(name, str(default)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# --- Service identity / OpenTelemetry resource ---------------------------------
SERVICE_NAME = _get("OTEL_SERVICE_NAME", "confpilot") or "confpilot"
SERVICE_VERSION = _get("SERVICE_VERSION", "0.1.0") or "0.1.0"
DEPLOYMENT_ENV = _get("DEPLOYMENT_ENV", "local") or "local"

# --- Elasticsearch -------------------------------------------------------------
ES_URL = _get("ES_URL")
ES_API_KEY = _get("ES_API_KEY")
ES_USERNAME = _get("ES_USERNAME")
ES_PASSWORD = _get("ES_PASSWORD")
ES_TIMEOUT = _float("ES_TIMEOUT", 3.0)
ES_INDEX_TALKS = _get("ES_INDEX_TALKS", "talks") or "talks"
ES_INDEX_ATTENDEES = _get("ES_INDEX_ATTENDEES", "attendees") or "attendees"
ES_INDEX_ROOMS = _get("ES_INDEX_ROOMS", "rooms") or "rooms"

# --- OpenAI-compatible LLM -----------------------------------------------------
LLM_BASE_URL = _get("LLM_BASE_URL")
LLM_API_KEY = _get("LLM_API_KEY")
LLM_MODEL = _get("LLM_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
LLM_EMBED_MODEL = _get("LLM_EMBED_MODEL", LLM_MODEL) or LLM_MODEL
LLM_TIMEOUT = _float("LLM_TIMEOUT", 30.0)

# --- OpenTelemetry -------------------------------------------------------------
OTEL_EXPORTER_OTLP_ENDPOINT = _get("OTEL_EXPORTER_OTLP_ENDPOINT")

# --- Feature tuning ------------------------------------------------------------
SEARCH_DEFAULT_K = _int("SEARCH_DEFAULT_K", 5)
RAG_TOP_K = _int("RAG_TOP_K", 5)
