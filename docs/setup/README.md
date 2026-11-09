# Setup — all track products

Do these **before 11:00 AM on Nov 9** (building starts then; submissions close 5:30 PM MT).
Facts below were checked against each vendor's live docs on 2026-11-09. Anything not confirmed is marked **UNVERIFIED**.

| # | Product | Track | Prize | Guide | Account needed? |
|---|---|---|---|---|---|
| 0 | Codex + DeepSeek subagents | how we build | — | [CODEX_AND_AGENTS.md](CODEX_AND_AGENTS.md) | OpenAI ($50 credits at event) |
| 1 | Gitar (by Sonar) | AI code review | $4,000 | [GITAR.md](GITAR.md) | Yes — sign in with GitHub |
| 2 | Dash0 | Observability | $4,000 | [DASH0.md](DASH0.md) | Yes — 14-day trial |
| 3 | Radar (by Skyhook) | Kubernetes / AI SRE | $4,000 | [RADAR.md](RADAR.md) | No — free, open source |
| 4 | Elasticsearch | Search + vector DB | $4,000 | [ELASTICSEARCH.md](ELASTICSEARCH.md) | Elastic Cloud trial, or local Docker |

Also in the running: Best Overall (NVIDIA DGX Spark) and Merge Forward / accessibility (iPad).

## Event-page prerequisites (from luma.com/cnh)
- Gitar (Sonar) and Dash0 accounts set up before you arrive.
- For Radar or Elasticsearch tracks: **Docker and a Kubernetes cluster ready**.
- Laptop + charger.

## Machine checklist
```bash
brew install kind helm kubectl-radar   # kind, helm and Radar are not installed yet on Zack's Mac
open -a Docker                          # Docker daemon must be running for kind + image builds
gh auth status && codex --version && kubectl version --client
```

## Secrets
Never commit secrets. Put them in `.env` (gitignored) — template in [`.env.example`](../../.env.example).
For Kubernetes, fill `deploy/base/secret.yaml` locally or create the secret with `kubectl create secret` (see RADAR.md).

## Team
Repo: github.com/zackhada/confpilot (private). Collaborators invited: osideskyler, crstall4, tannernielson27.
Everyone: accept the invite, then do Gitar setup is a one-time step for the repo owner.
