# Elasticsearch (search + vector DB) — Track 4, $4,000

**What it is:** open-source search engine and vector database: keyword (BM25), semantic/vector, or hybrid search, and the retrieval layer for RAG.

**What judges want**
1. Elasticsearch is the **core data layer**, not a side feature.
2. Smart search: keyword, semantic, vector or hybrid.
3. Makes conferences easier.

## Option A — Elastic Cloud (recommended)
1. Sign up at https://cloud.elastic.co/registration (free trial) and create the smallest deployment.
2. Create an API key (Security → API keys). Put in `.env`:
```bash
ES_URL=https://<deployment>.es.<region>.elastic-cloud.com
ES_API_KEY=<api key>
```

## Load the glossary
```powershell
cd es
uv sync
uv run python -m confpilot_es.bootstrap --glossary ..\content\glossary.json
```
This creates the five `confpilot-*` indices and stores one percolator query per term. Mappings,
queries and demo queries for Kibana: [`es/README.md`](../../es/README.md).

## Pin the embedding model
`semantic_text` uses a default inference endpoint if you don't set one, and the default depends on version:
| Deployment | Default `inference_id` |
|---|---|
| Elastic Cloud Hosted 9.4+ / Serverless | `.jina-embeddings-v5-text-small` |
| Elastic Cloud Hosted 9.3 | `.elser-2-elastic` |
| Elastic Cloud Hosted 9.0–9.2 | `.elser-2-elasticsearch` |
Run `GET _inference` on your deployment and pin that id in the mapping so indexing and queries always use the same model.

## Demo moment
Ask "¿cómo ordena los resultados?" in Ask your conference → hybrid search with RRF finds the English moment where RRF was explained. Show the percolator turning a spoken sentence into term ids.

Sources: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text · https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text-setup-configuration
