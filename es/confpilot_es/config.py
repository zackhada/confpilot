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


def _settings(*names: str) -> list[str | None]:
    """Each named setting from the environment, falling back to the file at ENV_FILE."""
    file_values = _read_env_file(Path(os.environ["ENV_FILE"])) if os.environ.get("ENV_FILE") else {}
    return [os.environ.get(name) or file_values.get(name) for name in names]


def load_config() -> EsConfig:
    """Read ES_URL and ES_API_KEY from the environment, falling back to the file at ENV_FILE."""
    url, api_key = _settings("ES_URL", "ES_API_KEY")
    if not url or not api_key:
        raise ConfigError("Set ES_URL and ES_API_KEY, or point ENV_FILE at a file that defines them.")
    return EsConfig(url=url, api_key=api_key)


@dataclass(frozen=True)
class LlmConfig:
    """An OpenAI-compatible chat completions endpoint."""

    base_url: str
    api_key: str
    model: str

    @property
    def extra_body(self) -> dict[str, object]:
        """Provider-specific request fields.

        Anthropic models think before answering by default, and that thinking is billed against
        `max_tokens`: with a small budget the visible reply comes back empty. These helpers are
        short formatting tasks, so thinking is switched off.
        """
        return {"thinking": {"type": "disabled"}} if "anthropic.com" in self.base_url else {}


def load_llm_config() -> LlmConfig:
    """Read LLM_BASE_URL, LLM_API_KEY and LLM_MODEL from the environment or the file at ENV_FILE."""
    base_url, api_key, model = _settings("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    if not base_url or not api_key or not model:
        raise ConfigError("Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL, or define them in the ENV_FILE file.")
    return LlmConfig(base_url=base_url.rstrip("/"), api_key=api_key, model=model)


def create_client(config: EsConfig | None = None) -> AsyncElasticsearch:
    resolved = config or load_config()
    return AsyncElasticsearch(resolved.url, api_key=resolved.api_key, request_timeout=REQUEST_TIMEOUT_S)
