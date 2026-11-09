# ConfPilot

**Stop nodding along.** ConfPilot decodes the conference jargon *you personally* don't know,
the moment it is said, then turns the conference into your own study plan.

Built at the Cloud Native Hackathon (WeMakeDevs, Salt Lake City, Nov 9 2026).
The full build, demo and pitch plan is in [docs/CONFPILOT_PLAN.md](docs/CONFPILOT_PLAN.md).

## What was built when

The hackathon rules say main coding must begin after kickoff (11:00 AM MT).

- **`reference/`** holds a scaffold committed between 9:09 and 9:35 AM, before kickoff, for an
  earlier idea (talk search and matchmaking). It is kept for transparency only. Nothing in it
  is built, imported, deployed or submitted, and CI fails if code outside `reference/` uses it.
- **Everything outside `reference/`** was written after 11:00 AM and landed through
  Gitar-reviewed pull requests. The commit history shows this.

## Layout

| Path | What | Owner |
| --- | --- | --- |
| `contracts/` | API and event shapes every part agrees on | all (change by PR) |
| `api/`, `es/` | FastAPI service and Elasticsearch layer | Zack |
| `web/`, `observability/` | Phone app (PWA), stage view, Dash0 dashboards and SLO | Tanner |
| `deploy/` | EKS, HTTPS, ECR, deploy workflows | Clayton |
| `content/`, `stt/`, `worker/`, `.gitar/`, `docs/` | Glossary, speech-to-text, LLM worker, review rules, docs | Skyler |
| `reference/` | Pre-kickoff scaffold, not part of the submission | nobody |

## Setup

Setup steps land with the first service PRs. Secrets are never committed: copy `.env.example`
to `.env` locally, and in the cluster they live in a Kubernetes Secret created by a human.

## AI disclosure

We used AI coding assistants throughout, as the rules allow: Claude Code, OpenAI Codex and
DeepSeek subagents. Humans set the plan, reviewed every pull request alongside Gitar, and can
explain the architecture.
