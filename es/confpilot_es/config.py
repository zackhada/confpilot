"""Connection settings. Secrets come from the environment or an ENV_FILE, never the repo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from elasticsearch import AsyncElasticsearch

DEFAULT_PREFIX = "confpilot-"
REQUEST_TIMEOUT_S = 30.0


class ConfigError(RuntimeError):
    """Raised when the Elasticsearch connection settings are missing."""


@dataclass(frozen=True)
class EsConfig:
    url: str
    api_key: str


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ConfigError(f"ENV_FILE does not exist: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.strip().partition("=")
        if separator and not key.startswith("#"):
            values[key.removeprefix("export ").strip()] = value.strip().strip("'\"")
    return values


def load_config() -> EsConfig:
    """Read ES_URL and ES_API_KEY from the environment, falling back to the file at ENV_FILE."""
    file_values = _read_env_file(Path(os.environ["ENV_FILE"])) if os.environ.get("ENV_FILE") else {}
    url = os.environ.get("ES_URL") or file_values.get("ES_URL")
    api_key = os.environ.get("ES_API_KEY") or file_values.get("ES_API_KEY")
    if not url or not api_key:
        raise ConfigError("Set ES_URL and ES_API_KEY, or point ENV_FILE at a file that defines them.")
    return EsConfig(url=url, api_key=api_key)


def create_client(config: EsConfig | None = None) -> AsyncElasticsearch:
    resolved = config or load_config()
    return AsyncElasticsearch(resolved.url, api_key=resolved.api_key, request_timeout=REQUEST_TIMEOUT_S)
