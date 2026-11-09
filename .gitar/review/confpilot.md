# ConfPilot review instructions

ConfPilot is an accessible AI conference companion: FastAPI backend + static accessible
frontend, Elasticsearch (hybrid BM25 + semantic_text search + RAG), Dash0 OpenTelemetry
end-to-end, Radar on Kubernetes, and every feature lands through Gitar-reviewed PRs.

## Timezone-safe session times (REQUIRED)
- All session times are stored and transmitted in **UTC** (ISO-8601 with `Z` or explicit `+00:00`).
- Any time the backend returns a time to the client, it must carry an **IANA timezone** for the
  event and the attendee's own timezone must be applied on the client (or via an explicit
  `tz` query parameter), never hard-coded to a single venue timezone.
- Flag any code that: stores local wall-clock time, formats datetimes without a timezone,
  does `new Date()`/`datetime.now()` without converting to the target zone, or assumes the
  conference venue timezone (Salt Lake City, America/Denver) applies to all attendees.
- Look for DST boundary bugs: prefer IANA zone names over fixed `UTC±n` offsets.

## API/frontend contract check (REQUIRED)
- The frontend consumes `/api/*` responses only through the typed schemas under
  `app/schemas/` (Pydantic) — the JSON keys must match exactly (snake_case).
- A PR that changes an endpoint's request/response shape MUST update the matching schema,
  the OpenAPI doc, AND the frontend fetcher in the same PR — flag any mismatch.
- Flag: silently changing a field name/type, adding required fields without a frontend change,
  returning bare `dict`/`JSONResponse` instead of the typed schema, or drifting from the
  example responses in `docs/`.

## OTel span required on new endpoints (REQUIRED)
- Every new/updated FastAPI route must produce a span (auto-instrumentation is the baseline;
  add a manual child span for any non-trivial unit of work: Elasticsearch calls, embedding
  calls, LLM/RAG calls, external fetches).
- Spans must set `service.name` and add useful attributes (e.g. `db.system`, `gen_ai.*`,
  query shape, result count). Flag routes that do I/O with no span or that swallow exceptions
  without recording them on the span (`span.record_exception`).

## Accessibility (ARIA) required on UI changes (REQUIRED)
- Screen-reader-first: every interactive control needs a programmatic name
  (`aria-label` / `aria-labelledby` / real text), visible focus, and keyboard operability.
- Dynamic updates (search results, filter changes, status messages) must use `aria-live`
  regions (`role="status"` / `role="alert"`) so changes are announced.
- Semantic landmarks: `<nav>`, `<main>`, `<header>`, `<footer>`; exactly one `<h1>`.
- Flag: `onclick` on a `<div>`/`<span>` with no `role`/`tabindex`/keyboard handler, images
  without meaningful `alt`, color-only indicators, and any new UI text without a plain-language
  summary option.

## General project gotchas
- Keep PRs small and single-purpose; do not bundle unrelated changes (the team merges ~10
  small PRs/day through Gitar).
- Do not commit secrets; read them from env. `.secrets/` is gitignored.
- Tests live beside the code (`tests/`); every endpoint change needs a test in the same PR.
