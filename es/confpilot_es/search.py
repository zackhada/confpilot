"""Utterance storage and "Ask your conference" hybrid search."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any

from confpilot_es.base import StoreBase
from confpilot_es.models import SearchHit, Speaker
from confpilot_es.telemetry import es_span

DEFAULT_SEARCH_SIZE = 10
MAX_SEARCH_SIZE = 50
RRF_RANK_WINDOW = 50
RRF_RANK_CONSTANT = 20


def hybrid_search_body(q: str, room: str, size: int) -> dict[str, Any]:
    """ "Ask your conference": BM25 and semantic retrievers fused with RRF, limited to one room.

    The semantic leg runs on a multilingual embedding, so a question in Spanish finds the
    English moment. Highlights come from the BM25 field, HTML-escaped, with <mark> tags.
    """
    lexical = {"multi_match": {"query": q, "type": "most_fields", "fields": ["text^2", "speaker.name"]}}
    semantic = {"semantic": {"field": "semantic_text", "query": q}}
    return {
        "retriever": {
            "rrf": {
                "retrievers": [{"standard": {"query": lexical}}, {"standard": {"query": semantic}}],
                "filter": {"term": {"room": room}},
                "rank_window_size": max(RRF_RANK_WINDOW, size),
                "rank_constant": RRF_RANK_CONSTANT,
            }
        },
        "size": size,
        "_source": ["utterance_id", "speaker", "spoken_at", "text", "term_ids"],
        "highlight": {
            "encoder": "html",
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
            "fields": {"text": {"number_of_fragments": 0, "highlight_query": {"match": {"text": q}}}},
        },
    }


class SearchMixin(StoreBase):
    async def index_utterance(
        self,
        utterance_id: str,
        room: str,
        speaker: Speaker | Mapping[str, Any],
        spoken_at: int,
        text: str,
        term_ids: Sequence[str] = (),
        word_to_card_ms: float | None = None,
        session_id: str | None = None,
    ) -> None:
        """Store one final utterance. Re-indexing the same `utterance_id` replaces it.

        `spoken_at` is epoch milliseconds in server time. `text` is also embedded into
        `semantic_text` by Elasticsearch at index time.
        """
        document = {
            "utterance_id": utterance_id,
            "room": room,
            "session_id": session_id,
            "speaker": Speaker.model_validate(speaker).model_dump(),
            "spoken_at": spoken_at,
            "text": text,
            "term_ids": list(term_ids),
            "word_to_card_ms": word_to_card_ms,
        }
        with es_span("es.index", operation="index_utterance", room=room, term_count=len(document["term_ids"])):
            await self.client.index(
                index=self.index("utterances"), id=utterance_id, document=document, refresh=self.refresh
            )

    async def search(self, q: str, room: str, size: int = DEFAULT_SEARCH_SIZE) -> list[SearchHit]:
        """Hybrid (BM25 + semantic, RRF) search over one room's utterances, best match first."""
        if not q.strip():
            return []
        body = hybrid_search_body(q, room, min(max(size, 1), MAX_SEARCH_SIZE))
        with es_span("es.search", operation="hybrid_search", room=room, query_length=len(q)) as span:
            response = await self.client.search(
                index=self.index("utterances"),
                retriever=body["retriever"],
                size=body["size"],
                source=body["_source"],
                highlight=body["highlight"],
            )
            hits = response["hits"]["hits"]
            span.set_attribute("confpilot.hit_count", len(hits))
            span.set_attribute("confpilot.es_took_ms", response["took"])
        return [_to_search_hit(hit) for hit in hits]


def _to_search_hit(hit: Mapping[str, Any]) -> SearchHit:
    source = hit["_source"]
    fragments = hit.get("highlight", {}).get("text")
    # A semantic-only hit (for example a Spanish question) has no keyword match to mark.
    highlight = fragments[0] if fragments else html.escape(source["text"])
    return SearchHit(
        utterance_id=source["utterance_id"],
        speaker=Speaker.model_validate(source["speaker"]),
        spoken_at=source["spoken_at"],
        text=source["text"],
        highlight=highlight,
        term_ids=source.get("term_ids") or [],
    )
