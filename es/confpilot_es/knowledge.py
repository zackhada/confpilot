"""Per-user knowledge (SM-2 state) and the room recap built from a terms aggregation."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from confpilot_es.base import StoreBase
from confpilot_es.models import HeardTerm, Knowledge, KnowledgePatch, Recap
from confpilot_es.telemetry import es_span

MAX_KNOWLEDGE_ITEMS = 2000
LEARN_NEXT_LIMIT = 5
MAX_HEARD_TERMS = 500


def recap_body(room: str) -> dict[str, Any]:
    """How often each glossary term was heard in a room, most heard first."""
    return {
        "size": 0,
        "query": {"term": {"room": room}},
        "aggs": {"heard": {"terms": {"field": "term_ids", "size": MAX_HEARD_TERMS}}},
    }


class KnowledgeMixin(StoreBase):
    async def get_knowledge(self, user_id: str) -> list[Knowledge]:
        """Everything recorded about what one user knows, ordered by term id."""
        with es_span("es.search", operation="get_knowledge"):
            response = await self.client.search(
                index=self.index("user-knowledge"),
                query={"term": {"user_id": user_id}},
                sort=[{"term_id": "asc"}],
                size=MAX_KNOWLEDGE_ITEMS,
            )
        return [Knowledge.model_validate(hit["_source"]) for hit in response["hits"]["hits"]]

    async def put_knowledge(self, user_id: str, term_id: str, patch: KnowledgePatch | Mapping[str, Any]) -> Knowledge:
        """Merge `patch` into the user's record for a term, creating it with SM-2 defaults.

        The document id is `"{user_id}:{term_id}"`, so there is exactly one per user and term.
        A field set to null in the patch (only `due_at` is nullable) is written as null.
        """
        changes = KnowledgePatch.model_validate(patch).model_dump(exclude_unset=True)
        created = Knowledge.model_validate({**changes, "user_id": user_id, "term_id": term_id})
        with es_span("es.index", operation="put_knowledge", term_id=term_id):
            response = await self.client.update(
                index=self.index("user-knowledge"),
                id=f"{user_id}:{term_id}",
                doc=changes,
                upsert=created.model_dump(),
                source=True,
                refresh=True,
                retry_on_conflict=3,
            )
        return Knowledge.model_validate(response["get"]["_source"])

    async def recap(self, room: str, user_id: str, learn_next_limit: int = LEARN_NEXT_LIMIT) -> Recap:
        """What was heard in a room, and what this user should learn next.

        `heard` is a terms aggregation over `term_ids`. `new_term_count` counts heard terms the
        user does not know. `learn_next` ranks by heard count x on-frontier, where a term is on
        the frontier when the user does not know it but knows all of its prerequisites.
        """
        heard, knowledge = await asyncio.gather(self._heard_terms(room), self.get_knowledge(user_id))
        known = {item.term_id for item in knowledge if item.status == "known"}
        prereqs = await self._prereqs([item.term_id for item in heard])
        frontier = [
            item.term_id
            for item in heard
            if item.term_id not in known and all(prereq in known for prereq in prereqs.get(item.term_id, []))
        ]
        return Recap(
            room=room,
            new_term_count=sum(1 for item in heard if item.term_id not in known),
            heard=heard,
            learn_next=frontier[: max(learn_next_limit, 0)],
        )

    async def term_counts(self, room: str) -> dict[str, int]:
        """How many utterances in the room mention each term id, most heard first."""
        return {item.term_id: item.count for item in await self._heard_terms(room)}

    async def _heard_terms(self, room: str) -> list[HeardTerm]:
        body = recap_body(room)
        with es_span("es.search", operation="recap_aggregation", room=room):
            response = await self.client.search(
                index=self.index("utterances"), query=body["query"], aggs=body["aggs"], size=0
            )
        buckets = response["aggregations"]["heard"]["buckets"]
        return [HeardTerm(term_id=bucket["key"], count=bucket["doc_count"]) for bucket in buckets]

    async def _prereqs(self, term_ids: list[str]) -> dict[str, list[str]]:
        if not term_ids:
            return {}
        with es_span("es.get", operation="term_prereqs", term_count=len(term_ids)):
            response = await self.client.mget(index=self.index("terms"), ids=term_ids, source=["prereqs"])
        return {doc["_id"]: doc["_source"].get("prereqs", []) for doc in response["docs"] if doc.get("found")}
