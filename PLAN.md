# Cloud Native Hackathon (WeMakeDevs, SLC, Mon Nov 9 2026) — Win Plan

## Strategy
Every project competes for Best Overall (NVIDIA DGX Spark) and enters EVERY sponsor track whose tool it genuinely uses.
So build ONE conference app that deeply uses all four sponsors + accessibility (Merge Forward, iPad):

**ConfPilot** — an accessible AI conference companion.
- Elasticsearch = core data layer: hybrid (BM25 + vector/semantic) talk search ("something on eBPF and security"), RAG assistant over talk abstracts, hallway matchmaker (attendee interests as vectors).
- Dash0 = OpenTelemetry end to end: traces/logs/metrics in backend, RUM in frontend, LLM calls traced (OpenLIT), "chaos" button injecting latency/errors, Agent0 finds the cause live; SLO + health dashboard.
- Radar = runs on Kubernetes with Radar connected; use Radar AI investigation on a real issue (e.g. OOMKilled embed worker / CrashLoop) and show findings.
- Gitar = every feature lands through a Gitar-reviewed PR; .gitar review instructions (timezone handling, API/frontend contract rule); break CI on purpose, let auto-apply fix it live.
- Merge Forward (accessibility): screen-reader-first UI, plain-language talk summaries, captions/transcript search, sensory-friendly "quiet room / crowd level" indicator, low-bandwidth mode, multilingual queries.

## Judges' criteria (verbatim themes)
- Gitar: features land through PRs it reviewed (not one PR at end); project-aware review rules; CI failure diagnosis + auto-apply.
- Dash0: depth of instrumentation (traces, logs, metrics, RUM); Agent0/MCP fixing something real during the day; observability is part of product; dashboard/SLO bonus.
- Radar: run on k8s w/ Radar; use UI + MCP while building; AI investigation of a real issue; show learnings.
- Elastic: ES is core, smart hybrid/semantic search.
- All: how well it makes conferences easier.

## Important
Features must land DURING the day via Gitar-reviewed PRs. Prep tonight = accounts, infra, skeleton, data, scripts. Keep feature code on branches ready to PR one-by-one tomorrow.

## Layout
- app/        FastAPI backend + static accessible frontend (agent: app)
- data/       talk dataset + ES ingestion/hybrid search (agent: data)
- deploy/     Dockerfiles, k8s manifests, kind script, OTel collector (agent: infra)
- docs/       SETUP.md accounts checklist, DEMO.md pitch script (agent: docs)
