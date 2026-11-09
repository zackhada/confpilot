# docs/ — ConfPilot prep docs (agent: docs)

Night-before + day-of planning for **ConfPilot**, the accessible AI conference companion
(see `../PLAN.md`). This folder is the `docs` agent's output per the PLAN.md layout.

## What's here

| File | What it is |
|---|---|
| `SETUP.md` | **Tonight's exact checklist** — Gitar, Dash0, Radar, Elastic accounts/infra, with URLs and flagged-unverified items |
| `GITAR_RULES.md` | Drop-in Gitar review instructions + repository rule + auto-apply criteria (timezone, API/frontend contract, OTel span, ARIA) |
| `PR_PLAN.md` | Ordered list of ~10 small feature PRs to land through Gitar, incl. the deliberate CI break (PR #9) for the auto-apply demo |
| `DEMO.md` | 3-minute pitch script with per-beat timing, hitting every judge criterion for all four tracks + accessibility |
| `TIMELINE.md` | Day schedule (kickoff 10:00 AM, lunch 2:00 PM) mapped to the PR order |

## How to use (in order)

1. **Tonight (Sun Nov 8):** run `SETUP.md` top-to-bottom. It creates the accounts, installs
   the tools, generates auth tokens, and wires both MCP servers into Claude Code.
2. **Tonight:** commit the Gitar config from `GITAR_RULES.md` into `.gitar/` and push.
3. **Tomorrow (Mon Nov 9):** follow `TIMELINE.md`; open/merge PRs per `PR_PLAN.md`.
4. **Demo time:** read `DEMO.md` verbatim — it's timed to exactly 3 minutes with fallback rails.

## Key decisions baked in

- **Region:** Dash0 `us-west-2.aws` (Oregon) — closest to SLC. Elastic deployment in the
  nearest available region.
- **Elastic `semantic_text`** uses an explicit `inference_id` (not the version-dependent
  default) so index + query embeddings stay consistent — see SETUP.md §4.3.
- **Deliberate CI break is PR #9**, staged early and opened *live* at the demo so judges watch
  Gitar diagnose + auto-apply in real time.
- **Radar investigations run from the laptop** (`kubectl radar`), because in-cluster Helm
  installs can't run AI investigations.

## Verification status

Everything in `SETUP.md` marked ✅ was verified against the vendor docs/web on Nov 8, 2026.
Items marked ⚠️ are **unverified** (exact UI labels, trial-plan feature limits, exact endpoint
ports, version-dependent defaults) — record what you actually see tonight and update the file.
