"""`EsStore`: the one object the API imports. Each mixin owns one slice of behaviour."""

from __future__ import annotations

from confpilot_es.config import DEFAULT_PREFIX, EsConfig, create_client
from confpilot_es.glossary import GlossaryMixin
from confpilot_es.knowledge import KnowledgeMixin
from confpilot_es.llm import LlmMixin
from confpilot_es.percolate import PercolateMixin
from confpilot_es.search import SearchMixin


class EsStore(GlossaryMixin, PercolateMixin, SearchMixin, KnowledgeMixin, LlmMixin):
    @classmethod
    def from_env(cls, prefix: str = DEFAULT_PREFIX, refresh: bool = False, config: EsConfig | None = None) -> EsStore:
        """Build a store from ES_URL and ES_API_KEY (or the file named by ENV_FILE)."""
        return cls(create_client(config), prefix=prefix, refresh=refresh)
