# TIMELINE.md — hackathon day (Mon Nov 9, 2026)

Kickoff **~10:00 AM** · Lunch **2:00 PM** · Demo prep from **~3:00 PM**.
All times Mountain (Salt Lake City, `America/Denver`). PR numbers reference docs/PR_PLAN.md.

---

## 9:30–10:00 — Pre-kickoff buffer (30m)
- Coffee. Boot the laptop: start kind cluster, Elasticsearch, backend, Dash0/RUM live.
- Open the tabs you'll demo: app, Dash0, Radar, GitHub PRs, Agent0.
- Dry-run the DEMO.md beats once (muted) so screens are warm.
- Confirm Gitar is reviewing (open a throwaway PR if you need a warm-up).

## 10:00–10:30 — Kickoff + setup (30m)
- Attend kickoff. Note any rule changes / judging logistics.
- Team sync: assign the four agents per PLAN.md layout — `app` (backend), `data` (ES/dataset),
  `infra` (deploy/k8s/OTel), `docs` (this folder).
- Repaste the two MCP servers if Claude Code lost them (`claude mcp list`).

## 10:30–11:15 — Land PR #1 and #2 (45m)
- **PR #1** `feat/ci-skeleton` (CI + `.gitar/` config) — first Gitar review. Merge it.
- **PR #2** `feat/backend-skeleton` (`/healthz` + OTel). Confirm spans in Dash0 **now**
  (de-risks the Dash0 track early).

## 11:15–12:00 — Land PR #3 and #4 (45m)
- **PR #3** `feat/es-hybrid-search` (ES client + hybrid query + semantic_text mapping).
- **PR #4** `feat/talks-dataset` (dataset + ingestion). Verify hybrid query returns eBPF talk.

## 12:00–12:45 — Land PR #5 and #6 (45m)
- **PR #5** `feat/search-api` (typed schema + contract test).
- **PR #6** `feat/accessible-ui` (ARIA search UI). Quick keyboard/screen-reader sanity check.

## 12:45–1:30 — Land PR #7 and #8 (45m)
- **PR #7** `feat/timezone-sessions` (UTC storage + IANA localization).
- **PR #8** `feat/dash0-rum-chaos` (RUM + chaos button). Test chaos → confirm the spike + span
  attributes; prep Agent0's prompt for the demo.

## 1:30–2:00 — Land PR #10 + stage PR #9 (30m)
- **PR #10** `feat/radar-repro` (kind + manifests + OOMKilled worker). Open Radar, confirm the
  crash loop is visible in **Issues**, run `radar diagnose` once to warm up.
- **Stage PR #9** (deliberate CI break) on a branch, but **do NOT open the PR yet** — it's the
  live auto-apply moment in the demo.

## 2:00–2:30 — LUNCH (30m) 🥪
- Step away. Leave the app + Dash0 + Radar running and collecting data (nice demo texture).

## 2:30–3:00 — Polish + buffer (30m)
- Merge PR #10. Re-run the contract + timezone tests. Tighten the accessibility flow.
- Write the DEMO.md one-liner on a sticky note. Confirm both MCP servers answer.
- Decide demo speaker; the others keep screens hot as backup operators.

## 3:00–3:45 — Full rehearsal (45m)
- Run DEMO.md end-to-end against the clock. Fix the slowest beat.
- Pre-fetch Agent0's answer and Radar's findings in background tabs (fallback rails).
- Record a 20s screen capture of the hybrid search as a safety net.

## 3:45–4:00 — Final green-check (15m)
- All 10 PRs merged (or 9 merged + PR #9 staged for the live break). CI green everywhere.
- `.secrets/` still gitignored. Demo URLs in one place.

## 4:00–6:00 — Judging window (flex)
- Demo slot: run DEMO.md (3 min) + Q&A.
- After demo: leave the app running for judges to poke at; keep the PR list + Dash0 + Radar on screen.

---

## What can slip / what can't

| Can slip (recover after lunch) | Cannot slip |
|---|---|
| PR #4 dataset size (30 talks is enough) | PR #1 (Gitar must review everything after) |
| Extra RAG polish | PR #2 (spans in Dash0 early de-risks the whole day) |
| Radar Traffic view (nice-to-have) | PR #9 staged before demo (live auto-apply) |
| SLO dashboard polish | PR #6 accessibility basics (ARIA + live region) |

## Hard deadlines
- **12:00** — Gitar has reviewed ≥3 PRs (proves "not one PR at the end").
- **1:30** — PR #9 staged; chaos + Radar repro confirmed working.
- **3:45** — rehearsal done; everything warm.
