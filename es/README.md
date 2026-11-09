# es/ — ConfPilot's Elasticsearch layer

Elasticsearch is ConfPilot's only database. This package (`confpilot_es`) owns the index
mappings and every query: live jargon detection with the **percolator**, "Ask your conference"
with **hybrid BM25 + semantic search fused by RRF** (multilingual), and the recap built from an
**aggregation**. It targets an Elastic Cloud Serverless project with the Elastic Inference Service.

## Setup

Credentials are read from `ES_URL` and `ES_API_KEY`, or from the file named by `ENV_FILE`.
Nothing secret lives in this directory.

```powershell
cd es
uv sync
$env:ENV_FILE = "C:\path\to\.env"          # defines ES_URL and ES_API_KEY
uv run python -m confpilot_es.bootstrap --glossary ..\content\glossary.json
uv run pytest -q -s                         # live tests; they skip when no credentials are set
```

`bootstrap` is idempotent: it creates missing indices, upserts every term and its percolator
query, and removes seed terms that left the glossary (terms the LLM added are kept).
`--recreate` drops and recreates **all five** indices, including utterances and user knowledge.
`--prefix` changes the index prefix. Tests use `confpilot-test-<run id>-*` and delete it afterwards.

## Indices

| Index | One document per | What it powers |
| --- | --- | --- |
| `confpilot-terms` | glossary term (`_id` = term id) | Cards, prerequisites; `semantic_text` = term + definition |
| `confpilot-term-queries` | term, as a stored **percolator** query over its spoken forms | Live detection |
| `confpilot-utterances` | final utterance | Search (`text` BM25 + `semantic_text`), recap (`term_ids`), latency |
| `confpilot-user-knowledge` | user and term (`_id` = `{user_id}:{term_id}`) | Personalization, SM-2 state |
| `confpilot-sessions` | talk or conversation | Recap metadata (mapping only for now) |

Both `semantic_text` fields use the inference endpoint `.jina-embeddings-v5-text-small`
(multilingual), named explicitly in `mappings/*.json`.

## Using it from the API

```python
from confpilot_es import EsStore

store = EsStore.from_env()  # one per process; `await store.close()` on shutdown
term_ids = await store.percolate("It uses BM 25 and R.R.F. to rank the results")  # ["bm25", "rrf"]
await store.index_utterance(utterance_id, room, speaker, spoken_at, text, term_ids)
hits = await store.search("¿cómo ordena los resultados?", room="slc1", size=5)
await store.put_knowledge(user_id, "rrf", {"status": "known", "source": "tap"})
recap = await store.recap(room="slc1", user_id=user_id)
```

Methods return the Pydantic models in `models.py`, which mirror `contracts/types.ts`
(`.model_dump()` gives the wire shape). Every call opens an OpenTelemetry span (`es.percolate`,
`es.search`, `es.index`, ...) with `confpilot.*` attributes, and failures raise `EsStoreError`.

## How matching works

The same rules as the phone (`contracts/README.md` section 6), proven by
`tests/test_percolate_live.py` running `contracts/fixtures/matcher_cases.json` against the cluster.

1. `normalizer.py` lowercases, strips punctuation, reads number words and joins spelled-out
   letters (`R.R.F.`, `r r f` -> `rrf`; `bm twenty five` -> `bm25`). Both the plain and the fully
   joined form are percolated, so `Kubernetes 1.30` still matches `kubernetes`.
2. Each term is a stored query: a phrase match per spoken form on a lowercased, ASCII-folded field.
   An ambiguous term with a `context` list is an `intervals` query (within five words of a context word).
3. `matching.py` applies the two rules that compare matches with each other: longest term first,
   and "an ambiguous term with no context list needs a non-ambiguous term of the same category
   within five words".

## LLM helpers (Elastic Inference Service)

`define_term(term, sentence)` returns a contract-shaped `Term` (`source: "llm"`, definition of 20
words or fewer) for a word the glossary lacks; pass it to `upsert_terms([term])` to make it a
glossary entry with its own percolator query. `translate_defs(terms, lang)` writes one-line
translations into `translations.<lang>`. Both call a `completion` inference endpoint
(`ES_LLM_ENDPOINT`, default `.anthropic-claude-5-sonnet-completion`) and must run async, never in
the request path.

**Status:** on the hackathon project every LLM endpoint (`completion` and `chat_completion`)
currently answers `403 Forbidden`, so these two are covered by stub tests only and
`tests/test_llm.py::test_define_and_translate_live` skips. Embedding endpoints are unaffected.

## Queries to show the judges

Paste into Kibana Dev Tools.

**1. Percolate: which glossary terms were just spoken?** The document is the utterance; the hits are terms.

```
GET confpilot-term-queries/_search
{
  "_source": ["term_id", "category", "ambiguous"],
  "query": { "constant_score": { "filter": { "percolate": {
    "field": "query",
    "document": { "text": ["it uses bm25 for keyword matches while the embeddings handle meaning and rrf to rank the results"] }
  } } } }
}
```

**2. A stored term query.** `GET confpilot-term-queries/_doc/rrf` shows the phrases; a common word
with explicit context is stored like this (from the sample glossary):

```
{ "intervals": { "text": { "all_of": { "ordered": false, "max_gaps": 4, "intervals": [
  { "any_of": { "intervals": [ { "match": { "query": "service", "ordered": true, "max_gaps": 0 } } ] } },
  { "any_of": { "intervals": [ { "match": { "query": "kubernetes" } }, { "match": { "query": "pod" } } ] } }
] } } } }
```

**3. Hybrid search with RRF, asked in Spanish, answered from English speech.**

```
GET confpilot-utterances/_search
{
  "size": 5,
  "retriever": { "rrf": {
    "retrievers": [
      { "standard": { "query": { "multi_match": {
          "query": "¿cómo ordena los resultados?", "type": "most_fields", "fields": ["text^2", "speaker.name"] } } } },
      { "standard": { "query": { "semantic": { "field": "semantic_text", "query": "¿cómo ordena los resultados?" } } } }
    ],
    "filter": { "term": { "room": "slc1" } },
    "rank_window_size": 50,
    "rank_constant": 20
  } },
  "highlight": { "encoder": "html", "pre_tags": ["<mark>"], "post_tags": ["</mark>"],
                 "fields": { "text": { "number_of_fragments": 0 } } }
}
```

**4. Recap: what did this room hear most?** Joined in `knowledge.py` with the user's known terms
and each term's `prereqs` to rank "learn next" (heard count x on the user's frontier).

```
GET confpilot-utterances/_search
{
  "size": 0,
  "query": { "term": { "room": "slc1" } },
  "aggs": { "heard": { "terms": { "field": "term_ids", "size": 500 } } }
}
```
