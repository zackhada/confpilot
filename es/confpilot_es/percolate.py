"""Live jargon detection: percolate one utterance against the stored term queries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from confpilot_es.base import StoreBase
from confpilot_es.matching import Candidate, resolve_matches
from confpilot_es.normalizer import variants
from confpilot_es.queries import percolate_body
from confpilot_es.telemetry import es_span


class PercolateMixin(StoreBase):
    async def percolate(self, text: str) -> list[str]:
        """Return the ids of the glossary terms spoken in `text`, in order of first appearance.

        The text is normalized exactly like the phone matcher (contracts/README.md section 6).
        Explicit `context` lists are enforced inside Elasticsearch by the stored `intervals`
        query; "longest term first" and the same-category rule for ambiguous terms without a
        context list are applied to the percolator hits afterwards (see `matching.py`).
        """
        forms = variants(text)
        if not forms:
            return []
        body = percolate_body(forms)
        with es_span("es.percolate", text_length=len(text)) as span:
            response = await self.client.search(
                index=self.index("term-queries"),
                query=body["query"],
                size=body["size"],
                source=body["_source"],
            )
            candidates = [_to_candidate(hit["_source"]) for hit in response["hits"]["hits"]]
            term_ids = resolve_matches(text, candidates)
            span.set_attribute("confpilot.match_count", len(term_ids))
            span.set_attribute("confpilot.candidate_count", len(candidates))
            span.set_attribute("confpilot.es_took_ms", response["took"])
        return term_ids


def _to_candidate(source: Mapping[str, Any]) -> Candidate:
    return Candidate(
        term_id=source["term_id"],
        phrases=tuple(source.get("phrases") or ()),
        category=source.get("category") or "",
        ambiguous=bool(source.get("ambiguous")),
        has_context=bool(source.get("context")),
    )
