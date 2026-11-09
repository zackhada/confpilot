# ConfPilot — hackathon repo (Cloud Native Hackathon, SLC, Nov 9 2026)

Goal: an app that makes conferences easier, using Gitar, Dash0, Radar and Elasticsearch genuinely.
Background, judging criteria and strategy: ../cnh-hackathon/PLAN.md and docs/.

## How work is split (IMPORTANT)
You (Codex) are the lead: plan, review, integrate, decide. Do the heavy lifting through
DeepSeek V4 Pro subagents (cheap) instead of writing big chunks yourself:

    bin/ds "task"                 # run a subagent and wait, prints its summary
    bin/ds -b -n search "task"    # run in background
    bin/ds-status                 # what is running / finished
    # logs: .agents/logs/<name>.log

Rules for delegating:
- Give each subagent one small, self-contained task with exact files and a definition of done.
- Parallel subagents must never touch the same files.
- Always review a subagent's diff (git diff) and run tests before committing. You own correctness.
- Do it yourself only when it's tiny, or when the subagent failed twice.

## Hackathon rules that shape the workflow
- Every feature lands as its own small PR on GitHub, reviewed by Gitar. Never one big PR.
  Flow: git switch -c feat/x -> subagent builds -> review -> push -> gh pr create -> address Gitar -> merge.
- New API endpoints need an OpenTelemetry span. UI changes need ARIA/keyboard support.
- Session times are stored with timezone (America/Denver), never naive.
- Elasticsearch is the core data layer, not a side feature.

## Layout
app/ backend + frontend · data/ talks dataset + ES ingest · deploy/ Docker, k8s, CI · docs/ setup, PR plan, demo
