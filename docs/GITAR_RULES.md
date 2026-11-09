# GITAR_RULES.md — ConfPilot review instructions + rules (drop-in)

These are the **draft** project-aware instructions for Gitar. They satisfy the judge criterion
"project-aware review rules" and the PLAN.md requirement (timezone handling, API/frontend contract,
OTel span on new endpoints, accessibility/ARIA on UI changes).

How to use:
- The block in **§1** goes to **`.gitar/review/confpilot.md`** (custom review instructions — Gitar reads it on every PR).
- The block in **§2** goes to **`.gitar/rules/confpilot-guardrails.md`** (automation rule with YAML frontmatter).
- The block in **§3** goes to **`.gitar/config/apply.md`** (per-repo auto-apply criteria).

All three are versioned in the repo and picked up automatically on the next PR. ✅ https://docs.gitar.ai/configuration/repository-config

---

## §1 — `.gitar/review/confpilot.md` (review instructions)

```markdown
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
```

---

## §2 — `.gitar/rules/confpilot-guardrails.md` (automation rule)

```markdown
---
title: "ConfPilot guardrails"
description: "Enforce timezone, contract, OTel, and accessibility conventions on ConfPilot PRs"
type: check
when: "Any PR that modifies app/ (backend), the frontend, or adds/changes an /api endpoint"
actions: "Post a checklist comment and add a needs-review label when a required convention is missing"
---

When a PR touches the backend or frontend:
- Verify every datetime returned to the client is UTC and timezone-aware (IANA zones).
- Verify any /api change updates the Pydantic schema, OpenAPI doc, and frontend fetcher together.
- Verify new endpoints emit an OTel span (auto or manual) with useful attributes.
- Verify UI changes include ARIA labels, aria-live for dynamic content, keyboard operability,
  and plain-language summaries.
- If any of these are missing, post a comment listing exactly what is missing and add the
  `needs-review` label.
- Skip this check for PRs that only touch docs/, .github/, or .gitar/.
```

> `needs-review` is just a suggested label — Gitar creates labels as needed. ✅ https://docs.gitar.ai/features/rules

---

## §3 — `.gitar/config/apply.md` (auto-apply criteria)

```markdown
Only auto-apply fixes that are minor and mechanical: unused imports, formatting/lint issues,
type errors, broken import statements, missing await, and failing tests. Never auto-apply
changes to authentication, payments, database migrations, or Elasticsearch mapping changes —
post those as review comments instead. Skip any finding in .gitar/, docs/, and .github/.
```

> Auto-apply criteria select fixes for **code-review findings only**; CI fixes and explicit
> `gitar fix` requests work independently of these criteria. ✅ https://docs.gitar.ai/features/code-review/auto-apply

---

## §4 — Commands to commit these tonight

```bash
mkdir -p .gitar/review .gitar/rules .gitar/config
# copy §1 → .gitar/review/confpilot.md
# copy §2 → .gitar/rules/confpilot-guardrails.md
# copy §3 → .gitar/config/apply.md
git add .gitar && git commit -m "Add Gitar review instructions, rules, and auto-apply criteria" && git push
```
