"""Settings, read from environment variables (and an optional local .env)."""

from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from confpilot import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = __version__
    static_dir: Path | None = None  # built web app, served at / with SPA fallback
    glossary_path: Path | None = None

    deepgram_api_key: SecretStr | None = None
    deepgram_token_ttl_s: int = 60

    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    probe_timeout_s: float = 6.0

    ws_heartbeat_s: float = 20.0

    session_secret: SecretStr | None = None  # unset: a random key per process
    session_ttl_s: int = 12 * 60 * 60
    rate_limit_per_minute: int = 20  # per client address (and per user where a route says so)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object, info) -> object:
        """`STATIC_DIR=` in a .env file means "not set", not the current directory."""
        if isinstance(value, str) and not value.strip():
            return cls.model_fields[info.field_name].default
        return value
