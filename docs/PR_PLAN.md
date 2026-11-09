# PR_PLAN.md — tomorrow's landing order (Mon Nov 9, 2026)

Goal: **~10 small feature PRs**, each merged through a Gitar-reviewed PR *during the day*
(the judge criterion is "features land through PRs Gitar reviewed — not one PR at the end").

Cadence: open the next PR as soon as the previous one is reviewed/merged. Keep each PR
single-purpose and <~150 changed lines so Gitar review is fast. Branch names below are
suggestions. Every PR opens against `main`.

| # | Branch | Title (one line) | Track(s) it proves | Gitar angle |
|---|---|---|---|---|
| 1 | `feat/ci-skeleton` | CI workflow + `.gitar/` config | Gitar | First Gitar review lands; rules are live |
| 2 | `feat/backend-skeleton` | FastAPI app + `/healthz` + OTel auto-instrumentation | Dash0, Gitar | "OTel span on new endpoint" rule fires |
| 3 | `feat/es-hybrid-search` | Elasticsearch hybrid search (BM25 + `semantic_text`) | Elastic | API contract rule fires |
| 4 | `feat/talks-dataset` | Talks dataset + ingestion script (semantic_text mapping) | Elastic | Real data, real embeddings |
| 5 | `feat/search-api` | `/api/search` typed schema + contract test | Gitar, Elastic | Contract check passes (schema+fetcher together) |
| 6 | `feat/accessible-ui` | Accessible search UI (ARIA, live regions, plain-language) | Accessibility | ARIA rule fires |
| 7 | `feat/timezone-sessions` | Timezone-safe session schedule endpoint | Gitar | Timezone rule fires |
| 8 | `feat/dash0-rum-chaos` | Dash0 RUM + "chaos" button (latency/errors) | Dash0 | OTel/RUM depth |
| 9 | `feat/agent0-incident` **(DELIBERATE CI BREAK)** | New endpoint with a broken import (CI fails on purpose) | Gitar | **CI failure diagnosis + auto-apply demo** |
| 10 | `feat/radar-repro` | kind + k8s manifests + OOMKilled/CrashLoop repro | Radar | Real k8s issue to investigate |

Deliberate break is **PR #9**, deliberately timed for the live auto-apply moment (see
DEMO.md 1:50–2:15 and TIMELINE.md ~1:30 PM). Everything else keeps CI green.

---

## PR 1 — `feat/ci-skeleton` — CI workflow + Gitar config (Gitar)
- `.github/workflows/ci.yml`: `actions/setup-python`, `pip install -r requirements.txt`, `ruff`/`black --check`, `pytest`.
- Commit `.gitar/review/confpilot.md`, `.gitar/rules/confpilot-guardrails.md`, `.gitar/config/apply.md` (from docs/GITAR_RULES.md).
- `AGENTS.md` one-pager: repo layout + the four conventions.
- **Demo beat**: open PR → Gitar posts dashboard comment → merge. Proves "features land through Gitar-reviewed PRs" from the first hour.

## PR 2 — `feat/backend-skeleton` — FastAPI + `/healthz` + OTel (Dash0, Gitar)
- `app/main.py` (FastAPI), `app/schemas/health.py`, `requirements.txt` (adds `dash0-opentelemetry`).
- `GET /healthz` returns `{"status":"ok","time":"<UTC ISO>"}` — **time is UTC** (exercises rule 1 early).
- Auto-instrument via `opentelemetry-instrument`; add a manual child span around a dummy work unit so the "span required" rule has something to verify.
- `.env.example` with `DASH0_*` vars (no secrets).
- **Demo beat**: spans appear in Dash0 → proves OTel end-to-end + "new endpoints emit spans".

## PR 3 — `feat/es-hybrid-search` — Elasticsearch hybrid search (Elastic)
- `app/elastic.py`: ES client (env-configured), `data/talks` index template with `semantic_text` on `abstract`/`summary` (explicit `inference_id` from SETUP.md §4.3).
- `app/search.py`: hybrid query = BM25 `multi_match` + `knn`/`semantic` query, fused (simple RRF or `bool should` + rescore).
- **Demo beat**: query "something on eBPF and security" returns talk → hybrid BM25+vector. Proves "ES is core + smart hybrid/semantic search".

## PR 4 — `feat/talks-dataset` — talks dataset + ingestion (Elastic)
- `data/talks.json` (~50–100 fake-but-realistic talks incl. eBPF, security, WASM, AI, databases), `data/ingest.py` bulk-loads into ES.
- Talks include: title, abstract, speaker, track, tags, room, and **UTC start/end + IANA zone**.
- **Demo beat**: re-index after PR 3, hybrid search returns relevant results.

## PR 5 — `feat/search-api` — `/api/search` typed schema + contract test (Gitar, Elastic)
- `app/schemas/search.py` (Pydantic `SearchRequest`/`SearchResponse`), `app/routers/search.py` (`POST /api/search`), `tests/test_search_contract.py`.
- **Contract test** asserts JSON keys == schema keys == what `frontend/` fetcher expects (this is the "API/frontend contract check" made real).
- **Demo beat**: point at the passing contract test in Gitar's Verification section.

## PR 6 — `feat/accessible-ui` — accessible search UI (Accessibility / Merge Forward)
- `frontend/` static page: search box + results list with `role="status"` live region, `aria-label`s, keyboard nav, skip-link, one `<h1>`, plain-language talk summaries, "quiet room / crowd level" indicator, low-bandwidth mode toggle.
- No new backend required (calls `/api/search` from PR 5).
- **Demo beat**: screen-reader + keyboard walkthrough (DEMO.md 2:15–2:45).

## PR 7 — `feat/timezone-sessions` — timezone-safe sessions (Gitar timezone rule)
- `app/routers/schedule.py`: `GET /api/schedule?tz=America/New_York` returns sessions localized to the attendee's IANA zone; stores only UTC.
- Tests for DST boundary + a non-venue timezone.
- **Demo beat**: show the same talk at different attendee timezones; point to the timezone review instruction Gitar enforced.

## PR 8 — `feat/dash0-rum-chaos` — Dash0 RUM + chaos button (Dash0)
- `frontend/`: `@dash0/sdk-web` `init()` with the RUM token; "chaos" button injects latency/500s (calls a `/api/chaos` endpoint).
- `app/routers/chaos.py`: `/api/chaos?mode=latency|error` — emits spans with the injected failure; always records the exception on the span.
- **Demo beat**: press chaos → latency/error spike in Dash0 RUM + traces; Agent0 explains it live.

## PR 9 — `feat/agent0-incident` — **DELIBERATE CI BREAK** (Gitar auto-apply demo)
- Add `app/routers/stats.py` with a **broken import** (`from app.nonexistent import metrics`) so `pytest`/`ruff` fails.
- Open the PR with the `gitar-managed` label **and** comment `gitar auto-apply:on`.
- **Live**: Gitar posts CI failure root cause, then auto-apply pushes a fix commit; show the fixed CI going green.
- **Fallback if auto-apply is plan-gated (see SETUP.md §6.1)**: comment `gitar fix this` and show the same diagnosis+fix flow.

## PR 10 — `feat/radar-repro` — kind + manifests + OOMKilled repro (Radar)
- `deploy/`: `kind` config, `deploy/kind.sh`, `deploy/k8s/*.yaml` (backend Deployment with a low memory limit + an embed-worker that OOMKills), `deploy/otel-collector.yaml`.
- `deploy/break.sh`: a script that sets `resources.limits.memory=64Mi` on the embed worker to force OOMKilled/CrashLoopBackOff.
- **Demo beat**: open Radar → Issues shows the crash loop → run `radar diagnose deploy/embed-worker -n confpilot` → show findings (DEMO.md 1:20–1:50).

---

## Ordering rationale
1. Infra + Gitar config first (PR 1) so **every later PR is reviewed by a rules-aware Gitar**.
2. Backend + OTel (PR 2) before features so **everything after is already instrumented**.
3. Elastic (PR 3–4) before the search API/UI (PR 5–6) so the UI has real data to render.
4. Timezone (PR 7) after the API exists, exercising the contract.
5. Chaos/RUM (PR 8) after UI exists so RUM has a page to monitor.
6. Deliberate break (PR 9) late — **after** judges have seen green PRs, so the auto-apply moment reads as "recovery", and CI history shows Gitar catching a real regression.
7. Radar repro (PR 10) last — gives Radar the most realistic (broken) cluster to investigate.
