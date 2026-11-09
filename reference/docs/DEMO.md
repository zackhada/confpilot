# DEMO.md — 3-minute pitch script (Mon Nov 9, 2026)

**One-liner:** *ConfPilot is an accessible AI conference companion — hybrid Elasticsearch
search + RAG, Dash0 observability end-to-end, Radar on Kubernetes, and every feature landed
through Gitar-reviewed PRs.*

Prep (before judges arrive): kind cluster up, backend running, ES index loaded, Dash0
receiving spans/RUM, Claude Code with both MCP servers connected, PR #9 staged (not yet opened).

---

## Timing map

| Time | Beat | Track / criterion hit |
|---|---|---|
| 0:00–0:15 | Hook + one-sentence pitch | All / "makes conferences easier" |
| 0:15–0:50 | Hybrid search + RAG | **Elastic** — ES core, hybrid BM25+semantic |
| 0:50–1:20 | Live traces + chaos + Agent0 | **Dash0** — depth, RUM, Agent0 fixes something real, dashboard |
| 1:20–1:50 | Radar on k8s + AI investigation | **Radar** — run on k8s, UI + MCP, AI investigation of a real issue |
| 1:50–2:15 | Gitar PRs + live CI break + auto-apply | **Gitar** — features via reviewed PRs, rules, CI diagnosis + auto-apply |
| 2:15–2:45 | Accessibility walkthrough | **Merge Forward** — ARIA, plain language, quiet-room, low-bandwidth, multilingual |
| 2:45–3:00 | Close + proof sentence | All |

---

## Script

### 0:00–0:15 — Hook (15s)
> "Conferences are chaotic. Finding the right talk is a full-text guessing game, the app
> breaks and nobody knows why, and — for attendees using screen readers — most conference
> apps are unusable. ConfPilot fixes all three, and we built it the way real teams ship:
> every feature landed through an AI-reviewed pull request."

(Point at the running app, already on screen.)

### 0:15–0:50 — Elastic: hybrid search + RAG (35s)
- Type the natural-language query: **"something on eBPF and security"**.
- *Say:* "This isn't keyword matching — Elasticsearch fuses BM25 with `semantic_text`
  vectors. 'eBPF' appears in the title, but 'security' is only *implied* by the abstract,
  and it still ranks first." (Click the result; highlight the matched semantic passage.)
- One more query: **"quiet low-key talk for an introvert"** → show the RAG assistant answer
  generated over talk abstracts (point at the citations under the answer).
- *Say:* "Elasticsearch is our core data layer — search, RAG, and the attendee matchmaker
  all run on it." ✅ Elastic criterion: core data layer + smart hybrid/semantic search.

### 0:50–1:20 — Dash0: traces + chaos + Agent0 (30s)
- Switch to the Dash0 dashboard. Point at the live **trace waterfall** for the search call
  you just made (FastAPI → Elasticsearch → embedding), plus RUM web-vitals and logs in one view.
- Press the **"Chaos"** button in the app. A latency/error spike appears live.
- *Say:* "Every new endpoint is required to emit an OTel span — our Gitar review rules
  enforce that. Now watch the part judges care about:" → open **Agent0**, type/paste
  *"why did /api/search start erroring in the last minute?"* and let it answer with the
  root cause (the injected fault) while you narrate.
- *Say:* "Observability isn't bolted on — it's part of the product, and our AI agent
  diagnoses it live." ✅ Dash0 criteria: depth (traces/logs/metrics/RUM), Agent0 fixing real
  issue, dashboard/SLO bonus (point at the health dashboard for 2s).

### 1:20–1:50 — Radar: k8s + AI investigation (30s)
- Switch to **Radar** (localhost:9280). The **Issues** queue shows `embed-worker`
  **OOMKilled / CrashLoopBackOff** (set up by PR #10).
- *Say:* "ConfPilot runs on Kubernetes, watched by Radar — no agents in the cluster, one
  binary on my laptop."
- Click **Investigate** (or run `radar diagnose deploy/embed-worker -n confpilot`).
  Claude Code walks the evidence: memory limit, the OOMKilled event, the diff that changed
  the limit. Show the **Findings** page with evidence per claim.
- *Say:* "Same live data in the UI, the MCP server, and the investigation — one model of
  the cluster." ✅ Radar criteria: k8s + Radar, UI + MCP while building, AI investigation of
  a real issue, show learnings.

### 1:50–2:15 — Gitar: reviewed PRs + live CI break + auto-apply (25s)
- Show the GitHub PR list: **PRs #1–#10 all merged today**, each with Gitar's dashboard
  comment (code review, Verification, rules).
- *Say:* "Ten features landed today, every one through a Gitar-reviewed PR — not one big
  PR at the end. And our `.gitar` rules are project-aware: timezone-safe times, API/frontend
  contract, OTel span required, ARIA required."
- **Live beat:** open PR #9 (already staged) — it breaks CI on purpose. Watch Gitar post
  the **CI failure root cause**, then (auto-apply on) push a fix commit; the CI check flips
  green. *Say:* "Gitar diagnosed the break and applied the fix itself." ✅ Gitar criteria:
  features via reviewed PRs, project-aware rules, CI failure diagnosis + auto-apply.

### 2:15–2:45 — Accessibility (Merge Forward) (30s)
- Turn on VoiceOver / NVDA (have it ready). Tab through the app: skip-link, one `<h1>`,
  focus ring visible, `role="status"` announcing search results.
- *Say:* "Screen-reader-first: every control is named, every dynamic update is announced."
- Show the **plain-language summaries** toggle, the **quiet-room / crowd-level** indicator,
  **low-bandwidth mode**, and a **multilingual** query (e.g. Spanish query → results).
- *Say:* "We treat accessibility as a first-class feature, and our Gitar rules block any UI
  change that ships without ARIA." ✅ Merge Forward + the all-track "makes conferences easier."

### 2:45–3:00 — Close (15s)
> "ConfPilot: Elasticsearch as the brain, Dash0 as the nervous system, Radar as the
> diagnostic camera, Gitar as the teammate who reviewed every line — and accessibility
> built in, not bolted on. Every feature you saw shipped today, through AI-reviewed PRs."

---

## Criterion → beat cheat-sheet (for Q&A)

| Judge criterion (verbatim theme) | Where we show it |
|---|---|
| Gitar: features land through PRs it reviewed (not one PR at end) | 1:50 PR list (#1–#10, all reviewed today) |
| Gitar: project-aware review rules | 1:50 `.gitar` rules (timezone/contract/OTel/ARIA) |
| Gitar: CI failure diagnosis + auto-apply | 1:50 live PR #9 break → diagnosis → auto-fix |
| Dash0: depth (traces/logs/metrics/RUM) | 0:50 unified dashboard + trace waterfall + RUM |
| Dash0: Agent0/MCP fixing something real during the day | 0:50 chaos → Agent0 root-cause |
| Dash0: observability is part of product; dashboard/SLO bonus | 0:50 "not bolted on" + health dashboard |
| Radar: run on k8s w/ Radar | 1:20 kind cluster + Radar Issues |
| Radar: use UI + MCP while building | 1:20 Investigate button + Claude Code MCP |
| Radar: AI investigation of a real issue; show learnings | 1:20 OOMKilled findings page |
| Elastic: ES is core, smart hybrid/semantic search | 0:15 hybrid query + RAG |
| All: makes conferences easier | 0:00 + 2:15 accessibility + 2:45 close |

## Safety rails
- **If Agent0 is slow**, have its answer pre-fetched on a second tab and narrate over it.
- **If auto-apply is plan-gated** (SETUP.md §6.1), comment `gitar fix this` on PR #9 and show
  the same diagnosis → fix commit flow.
- **If Radar investigation stalls**, fall back to the read-only MCP in Claude Code:
  "what's unhealthy in kind-confpilot?" and show the `diagnose` output.
- **If live search fails**, show the pre-recorded query + results video (record one tonight).
