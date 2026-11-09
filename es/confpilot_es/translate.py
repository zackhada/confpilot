"""Translate glossary definitions with the LLM and store them on the terms."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from confpilot_es.llm import LlmError, LlmMixin, parse_json_object
from confpilot_es.models import Term
from confpilot_es.telemetry import EsStoreError, es_span

Lang = Literal["es", "zh", "hi", "pt"]

TRANSLATE_MAX_TOKENS = 2000
TRANSLATE_BATCH_SIZE = 20
TRANSLATE_CONCURRENCY = 2
LANGUAGE_NAMES: dict[str, str] = {
    "es": "Spanish",
    "zh": "Simplified Chinese",
    "hi": "Hindi",
    "pt": "Brazilian Portuguese",
}

_TRANSLATE_PROMPT = """Translate each glossary definition into {language} for a conference attendee.
Keep each translation to one short, plain line. Keep product names and acronyms in English.
Reply with one JSON object and nothing else, mapping each "id" to its translation.

{items}"""


class TranslateMixin(LlmMixin):
    async def translate_defs(
        self, terms: Sequence[Term | Mapping[str, Any]], lang: Lang, save: bool = True
    ) -> dict[str, str]:
        """Translate each term's `simple_def` into one line of `lang`. Returns `{term_id: line}`.

        Terms go to the model about 20 at a time. With `save` (the default) the lines are also
        written to `translations.<lang>` in the terms index, so `get_glossary()` serves them.
        A term the model skips is left out of the result.
        """
        if lang not in LANGUAGE_NAMES:
            raise ValueError(f"Unsupported language '{lang}'. Expected one of {sorted(LANGUAGE_NAMES)}.")
        parsed = [Term.model_validate(term) for term in terms]
        batches = [parsed[i : i + TRANSLATE_BATCH_SIZE] for i in range(0, len(parsed), TRANSLATE_BATCH_SIZE)]
        limit = asyncio.Semaphore(TRANSLATE_CONCURRENCY)

        async def translate_batch(batch: list[Term]) -> dict[str, str]:
            items = json.dumps(
                [{"id": term.id, "term": term.term, "definition": term.simple_def} for term in batch],
                ensure_ascii=False,
            )
            prompt = _TRANSLATE_PROMPT.format(language=LANGUAGE_NAMES[lang], items=items)
            async with limit:
                reply = await self._complete(prompt, "translate", TRANSLATE_MAX_TOKENS)
            try:
                lines = parse_json_object(reply)
            except ValueError as exc:
                raise LlmError(f"llm.translate returned an unusable batch: {exc}") from exc
            wanted = {term.id for term in batch}
            return {key: str(value).strip() for key, value in lines.items() if key in wanted and str(value).strip()}

        results = await asyncio.gather(*(translate_batch(batch) for batch in batches))
        translations = {term_id: line for result in results for term_id, line in result.items()}
        if save and translations:
            await self._save_translations(translations, lang)
        return translations

    async def _save_translations(self, translations: Mapping[str, str], lang: Lang) -> None:
        operations: list[dict[str, Any]] = []
        for term_id, line in translations.items():
            operations.append({"update": {"_index": self.index("terms"), "_id": term_id}})
            operations.append({"doc": {"translations": {lang: line}}})
        with es_span("es.index", operation="save_translations", term_count=len(translations)):
            response = await self.client.bulk(operations=operations, refresh=True)
        if response.get("errors"):
            failed = [item["update"]["_id"] for item in response["items"] if "error" in item["update"]]
            raise EsStoreError(f"es.index failed to save translations for {len(failed)} terms; first: {failed[0]}")
