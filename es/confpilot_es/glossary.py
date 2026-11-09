"""Index lifecycle and glossary loading: `terms` plus one percolator query per term."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from opentelemetry import trace

from confpilot_es.base import INDEX_NAMES, StoreBase, load_index_body
from confpilot_es.models import Glossary, Term
from confpilot_es.queries import percolator_doc, term_doc
from confpilot_es.telemetry import EsStoreError, es_span

logger = logging.getLogger(__name__)

MAX_GLOSSARY_TERMS = 2000
UNVERSIONED = "unversioned"


class GlossaryMixin(StoreBase):
    async def ensure_indices(self, recreate: bool = False) -> list[str]:
        """Create the five indices if they are missing. Returns the names that were created."""
        created: list[str] = []
        for name in INDEX_NAMES:
            index = self.index(name)
            with es_span("es.indices.ensure", index=index, recreate=recreate):
                if recreate:
                    await self.client.options(ignore_status=404).indices.delete(index=index)
                if await self.client.indices.exists(index=index):
                    continue
                body = load_index_body(name)
                await self.client.indices.create(index=index, mappings=body["mappings"], settings=body.get("settings"))
                created.append(index)
        return created

    async def delete_indices(self) -> None:
        """Delete every index under this store's prefix (used by tests)."""
        for name in INDEX_NAMES:
            with es_span("es.indices.delete", index=self.index(name)):
                await self.client.options(ignore_status=404).indices.delete(index=self.index(name))

    async def upsert_terms(self, terms: Iterable[Term | Mapping[str, Any]], version: str | None = None) -> int:
        """Index terms and register their percolator queries. Safe to call again with the same terms."""
        parsed = [Term.model_validate(term) for term in terms]
        operations: list[dict[str, Any]] = []
        for term in parsed:
            operations.append({"index": {"_index": self.index("terms"), "_id": term.id}})
            operations.append(term_doc(term))
            operations.append({"index": {"_index": self.index("term-queries"), "_id": term.id}})
            operations.append(percolator_doc(term))
        if operations:
            with es_span("es.index", operation="upsert_terms", term_count=len(parsed)) as span:
                response = await self.client.bulk(operations=operations, refresh=True)
                try:
                    _raise_on_bulk_errors(response)
                except EsStoreError as exc:
                    span.record_exception(exc)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                    raise
        if version is not None:
            with es_span("es.indices.put_mapping", glossary_version=version):
                await self.client.indices.put_mapping(index=self.index("terms"), meta={"glossary_version": version})
        return len(parsed)

    async def prune_seed_terms(self, keep_ids: Iterable[str]) -> int:
        """Delete seed terms (and their queries) that are no longer in the glossary.

        Terms the LLM added (`source: "llm"`) are kept. Returns how many terms were removed.
        """
        stale = {
            "bool": {
                "filter": [{"term": {"source": "seed"}}],
                "must_not": [{"ids": {"values": list(keep_ids)}}],
            }
        }
        removed = 0
        for name in ("terms", "term-queries"):
            with es_span("es.delete", operation="prune_seed_terms", index=self.index(name)):
                response = await self.client.delete_by_query(
                    index=self.index(name), query=stale, refresh=True, conflicts="proceed"
                )
            removed = max(removed, response["deleted"])
        return removed

    async def get_glossary(self) -> Glossary:
        """The whole glossary, as served by `GET /api/glossary`."""
        index = self.index("terms")
        with es_span("es.search", operation="get_glossary"):
            mapping = await self.client.indices.get_mapping(index=index)
            response = await self.client.search(
                index=index,
                query={"match_all": {}},
                sort=[{"id": "asc"}],
                size=MAX_GLOSSARY_TERMS,
                source_excludes=["semantic_text"],
            )
        meta = next(iter(mapping.body.values()))["mappings"].get("_meta", {})
        terms = [Term.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]
        return Glossary(version=meta.get("glossary_version", UNVERSIONED), terms=terms)


def _raise_on_bulk_errors(response: Mapping[str, Any]) -> None:
    if not response.get("errors"):
        return
    failures = [
        f"{action['_index']}/{action['_id']}: {action['error'].get('reason', action['error'])}"
        for item in response["items"]
        for action in item.values()
        if "error" in action
    ]
    logger.error("Bulk index failed for %d documents", len(failures))
    raise EsStoreError(f"es.index failed for {len(failures)} documents; first: {failures[0]}")
