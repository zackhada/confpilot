# data/ — CloudNative Summit SLC 2026 dataset + Elasticsearch hybrid search

Dataset and ingestion/search tooling for the **ConfPilot** conference companion.
This directory is self-contained: it generates a realistic conference dataset,
loads it into Elasticsearch with BM25 + semantic/vector search, and demonstrates
hybrid retrieval with Reciprocal Rank Fusion (RRF).

## What's here

| File               | Purpose                                                                 |
|--------------------|-------------------------------------------------------------------------|
| `generate_data.py` | Deterministic generator for `talks.json` + `attendees.json`             |
| `talks.json`       | **150 talks** — id, title, abstract, speakers, track, room, start_time (ISO8601, America/Denver = `-07:00` MST in Nov), level, tags |
| `attendees.json`   | **60 attendees** — id, name, role, company, interests                    |
| `ingest.py`        | Creates `talks` (+ `attendees`) index, bulk-loads the data               |
| `search.py`        | Hybrid BM25 + vector/semantic search with RRF                            |
| `docker-compose.yml` | Single-node Elasticsearch 8.16.1, security off for dev                 |
| `requirements.txt` | Python deps (`elasticsearch`, `sentence-transformers`)                   |

## The dataset

- 10 tracks × 15 talks = 150 talks (Kubernetes, eBPF & Kernel, Security,
  Observability, AI Infrastructure, Platform Engineering, Networking,
  Serverless & Edge, Developer Experience, Data & Streaming).
- Each track maps to a room; 8 talks/room on Mon **2026-11-09**, 7 on Tue
  **2026-11-10** (07:00–18:00 range).
- `start_time` uses the IANA zone **America/Denver**. Denver is on MST
  (UTC-07:00) in November, so the ISO8601 offset is `-07:00` (e.g.
  `2026-11-09T09:00:00-07:00`).
- Attendee `interests` overlap heavily with talk `tags` so interest-based
  search and hallway matchmaking work out of the box.

Regenerate the data (idempotent, fixed seed):

```bash
python3 generate_data.py
```

## Run it

### 1. Start Elasticsearch (security off, dev)

```bash
docker compose up -d
curl http://localhost:9200        # wait for {"name":...}
```

### 2. Install Python deps

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Ingest

```bash
python3 ingest.py                 # talks + attendees
python3 ingest.py --drop          # recreate from scratch
python3 ingest.py --skip-attendees
```

`ingest.py` picks its semantic strategy automatically:

1. **`semantic_text`** — if a `text_embedding`/`sparse_embedding` inference
   endpoint exists on the cluster (ES ≥ 8.15). Point at one with
   `ES_INFERENCE_ID=<id>`, or pass `--create-inference` to try deploying
   E5/ELSER for you.
2. **`dense_vector` fallback** — otherwise, a 384-dim `dense_vector`
   (`content_vector`) is populated locally with
   `sentence-transformers/all-MiniLM-L6-v2`. No cluster-side model needed.

### 4. Search (hybrid + RRF)

```bash
python3 search.py "something on eBPF and security"
python3 search.py "scaling kubernetes to thousands of nodes" --track Kubernetes --level Advanced
python3 search.py "cost of observability" --size 5 --compare   # hybrid vs BM25-only
python3 search.py "vector search" --no-vector                  # BM25 only
```

`search.py` detects the ingest mode from the index mapping and builds the right
retriever:

- ES **≥ 8.16** → `retriever` RRF API (`standard` BM25 + `semantic`/`knn`).
- ES **8.8–8.15** with `dense_vector` → `rank.rrf` (`query` + `knn`).
- ES **8.15** with `semantic_text` → weighted bool fallback (RRF isn't in 8.15).

## Environment variables

| Var               | Default                    | Meaning                              |
|-------------------|----------------------------|--------------------------------------|
| `ES_URL`          | `http://localhost:9200`    | Elasticsearch endpoint               |
| `ES_API_KEY`      | (unset)                    | Optional API key (not needed here)   |
| `ES_INFERENCE_ID` | (unset)                    | Force a specific inference endpoint  |

## Notes

- The `dense_vector` fallback path requires `sentence-transformers` (downloads
  `all-MiniLM-L6-v2`, ~80 MB, on first use). The native `semantic_text` path
  does not.
- To use E5/ELSER inference natively, start ES with ≥ 2 GB heap
  (`ES_JAVA_OPTS=-Xms2g -Xmx2g` in `docker-compose.yml`) and internet access for
  the one-time model download, then run `python3 ingest.py --create-inference`.
- BM25 works on `title`, `abstract`, `tags`, `speakers`, `track`; semantic/vector
  search runs over title+abstract (talks) or interests (attendees).
