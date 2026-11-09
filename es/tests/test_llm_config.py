"""LLM settings come from the environment (or ENV_FILE), like the Elasticsearch ones."""

from __future__ import annotations

import pytest

from confpilot_es.config import ConfigError, LlmConfig, load_llm_config

CONFIG = LlmConfig(base_url="https://llm.test/v1", api_key="test-key", model="test-model")


def test_llm_config_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "ENV_FILE"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigError, match="LLM_BASE_URL, LLM_API_KEY and LLM_MODEL"):
        load_llm_config()
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.test/v1/")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "m")
    assert load_llm_config() == LlmConfig(base_url="https://llm.test/v1", api_key="k", model="m")


def test_thinking_is_switched_off_for_anthropic_only() -> None:
    anthropic = LlmConfig(base_url="https://api.anthropic.com/v1", api_key="k", model="m")
    assert anthropic.extra_body == {"thinking": {"type": "disabled"}}
    assert CONFIG.extra_body == {}
