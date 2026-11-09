# Cloud Native Hackathon — everything that decides whether we win

Source: https://www.wemakedevs.org/hackathons/cnh (+ `/rules`, `/schedule`, `/resources`, `/submit`) and the Radar starter repo https://github.com/skyhook-io/cnh-starter. Pulled 2026-11-09.

**Theme:** "Conferences, the easy way." Build something that makes conferences easier.
**When/where:** Mon Nov 9, 2026 · The Shop Workspace, 350 E 400 S, Salt Lake City · in person only · venue caps at 170–200 people, no entry once full.

---

## ⚠️ Rules that can disqualify us (read first)

1. **Main coding and design must begin after the hackathon starts.** Ideas, notes, sketches and research beforehand are fine.
   → Code written before 11:00 AM (the `app/`, `data/`, `deploy/` scaffold in this repo) should **not** be the submission. Treat it as research/reference; start the real build after kickoff (see "What this means for us" below).
2. Frameworks, OSS libraries, public APIs, templates, third-party tools and public assets are allowed. **Original work done during the hackathon is what gets judged.**
3. **Every submission needs a public source-code repo and a README with setup instructions.** (This repo is private right now.)
4. Only use data/tools/accounts you own or may use. **No private, personal or login-protected info in the repo or demo.**
5. **AI coding assistants are allowed but their use must be disclosed.**
6. **You must understand the code and be able to explain the architecture and technical decisions.**
7. Projects generated entirely by AI, without meaningful participant contribution, verification or understanding, **may be rejected**.
8. One project per team. Duplicate, copied or **previously finished projects are disqualified**.
9. Keyboard requires submitting a valid project.
10. IP belongs to the team — agree on ownership inside the team before submitting.
11. Respect everyone; plagiarism or manipulating judging = disqualified.
12. WeMakeDevs has final say on eligibility and judging.

---

## Schedule (Mountain Time)

| Time | What |
|---|---|
| 9:00 AM | Check-in, breakfast (arrive by 9:30) |
| 10:00 AM | Kickoff + talks — incl. **"Give your agent Radar: ship and debug on Kubernetes"** (Nadav Erell & Roy Libman, 15 min): team environments, connecting your agent, live broken-release demo. **Radar join code is given here.** |
| 11:00 AM – 2:00 PM | Build time |
| 2:00 PM | Lunch, panel (Kelsey Hightower), more build time |
| **5:30 PM** | **Submission deadline** (https://www.wemakedevs.org/hackathons/cnh/submit) |
| 5:30 – 6:30 PM | **Project presentations** (live) |
| 6:30 – 7:00 PM | Winners announced |
| After 7:00 PM | After-party: House of Kube (sign up on Luma, free, no KubeCon ticket needed) |

---

## Prizes

| Prize | What |
|---|---|
| Best project overall (any track) | NVIDIA DGX Spark personal AI supercomputer |
| Track 1 · AI code review (Gitar / Sonar) — "Never Merge Broken" | $4,000 |
| Track 2 · Observability (Dash0) — "Stop Flying Blind" | $4,000 |
| Track 3 · Kubernetes UI / AI SRE (Radar / Skyhook) | $4,000 |
| Track 4 · Search & vector DB (Elasticsearch) — "Find the Right Talk" | $4,000 |
| Merge Forward — "Conferences for Everyone" | iPad, for the project that makes conferences more inclusive and accessible |
| Top 10 projects | Signed *Kubernetes: Up & Running* (Kelsey Hightower) |
| Everyone in person | Keychron keyboard, **$50 OpenAI credits**, swag, certificate |

A project **enters every sponsor track whose tool it genuinely uses**, plus Merge Forward. Every project is in the running for best overall.

---

## Judges

Kelsey Hightower (ex-Google Cloud, KubeCon co-founder) · Wes Novack (SVP Engineering) · Joseph Sandoval (Adobe, CNCF End User TAB vice chair) · Saiyam Pathak (Kubesimplify, CNCF Ambassador) · Phil Estes (AWS) · Jacquie Capur (Nebius DevRel) · Tomás Martín Barreiro Iffernet (Cline) · Simon Schrottner (Flagsmith) · **Julia Furst Morgado (Dash0)** · Justin Garrison (Sidero Labs) · **Nadav Erell (CEO, Skyhook Radar)** · Kunal Kushwaha (WeMakeDevs)

---

## Judging criteria (verbatim from the page)

### Track 1 — Gitar: Never Merge Broken
- Gitar is part of how you built, with features landing through PRs it reviewed, **not one PR at the end**.
- Project-aware setup, with review instructions and repository rules that reflect how your team actually works.
- Using CI failure diagnosis and auto-apply to fix real problems.
- How well your project makes conferences easier.

### Track 2 — Dash0: Stop Flying Blind
- Depth of instrumentation across your app, including traces, logs, metrics and real-user monitoring if you have a frontend.
- Using Agent0 or the MCP server to find and fix something real during the day, **and showing it in your demo**.
- Observability that's part of the product experience, not bolted on at the end.
- **Bonus point** for a dashboard or an SLO that shows how healthy your app is.
- How well your project makes conferences easier.

### Track 3 — Radar: AI SRE
- Run your project on Kubernetes with Radar connected, in the cluster and namespace **they provide your team**, or on your own cluster.
- Use Radar's UI and MCP **throughout** building and operating. Show how Radar helped you ship, troubleshoot, or improve.
- Use Radar's AI investigations on a real issue or question about your running app. Show what you learned and what you did with the findings.
- Build something that makes conferences easier.

### Track 4 — Elasticsearch: Find the Right Talk
- Elasticsearch is the **core data layer** of your app, not a side feature.
- Smart use of search: keyword, semantic, vector or hybrid.
- How well your project makes conferences easier.

### Merge Forward
- Makes conferences more inclusive and accessible. (Merge Forward = CNCF community for underrepresented folks: Women in Cloud Native, Neurodiversity, Deaf and Hard of Hearing groups.)

---

## Sponsor-provided ideas (signals of what judges like)

**Gitar:** schedule builder where every feature lands via Gitar-reviewed PR with review instructions enforcing correct time zones · repo rule that fires when the API changes and checks the frontend still matches · break CI on purpose and let auto-apply fix it **live in the demo**.

**Dash0:** self-diagnosing multi-service app with a **"chaos" button** injecting latency/errors, Agent0 finds the cause in the demo · live crowd map where check-ins become metrics on a Dash0 dashboard · schedule app where Agent0 explains why "My agenda" slowed after the keynote · attendee AI assistant traced with **OpenLIT** (every LLM call, token, cost in Dash0).

**Radar (on Kubernetes):** talk picker that reads your GitHub, builds your schedule, reshuffles when a room fills · hallway-track matchmaker · live crowd map (packed rooms, shortest coffee line).

**Elasticsearch:** talk search where "something on eBPF and security" finds the right session even without those words · hallway matchmaker storing what everyone works on as vectors · conference assistant answering schedule questions with RAG over every talk abstract.

---

## How each sponsor says to use it (from /resources)

### Gitar
- Install Gitar as a **GitHub App on the hackathon repo**, ship **every feature as a PR**.
- Conventions → `.gitar/review/`; repository rules for repeatable workflow actions; **turn on auto-apply** so Gitar diagnoses failing CI and pushes the fix.
- Runs in the browser, nothing to install. **Free 14-day Gitar Pro trial, no card, includes auto-apply and custom rules.**

### Dash0
- Point OpenTelemetry auto-instrumentation at the app **in the first hour**.
- When something's slow/broken, ask **Agent0** why → root cause → have it **open a PR with the fix**.
- Connect the **MCP server** to your coding assistant so it reads live traces/logs.
- Features to use: Agent0, Dash0 MCP. Bonus: Dash0 CLI, dashboards, alerts, synthetic monitoring. Also: website monitoring (RUM), Dash0 Operator for Kubernetes.

### Radar
- Get a team environment (a **vcluster where you're cluster-admin**) at **https://join.cnh.radarhq.io** — join code at kickoff / Radar table; takes 3–4 min; status at `join.cnh.radarhq.io/status/<team-name>`. Or connect your own cluster to a free Radar Cloud org. A cluster of your own is optional.
- Copy the **starter repo** https://github.com/skyhook-io/cnh-starter ("Use this template", **must be public** so Argo CD can read it). Every push to `main` deploys through **Argo CD**; image builds to GHCR (must be public).
- Connect agent: `claude mcp add --scope user radar-cloud --transport http https://api.radarhq.io/mcp` → `/mcp` → authenticate → org **Cloud Native Hackathon**. Other agents (Codex): Radar Cloud → **Agents**. Every MCP call must pass **your cluster id** (~40 clusters in the org).
- Features to use: **AI investigations**, **Radar MCP** (ship, sync Argo CD, check each rollout), **Issues, Timeline, Checks**.
- Starter repo's plan for the day:
  - 11:00: before writing code, get cluster, open in Radar Cloud, connect agent.
  - First hour: open **Checks**, screenshot = your "before".
  - All day: agent pushes/syncs/waits on rollouts through Radar MCP; investigate anything unexplained. **Run at least one investigation (judges look for it).** Nothing broke? Investigate after a release — an all-clear with evidence counts.
  - By 5:30: tell the day's story from Radar — **timeline, investigation, Checks before/after.** Agent can draft "your 5:30 story".
  - Investigations start **private** — the person who started it must present it or mark it Shared.
- **Secrets:** repo and image are public → API keys only in a Kubernetes Secret (`app-credentials` in `team-<team-name>`), never in code/Dockerfile/commits/logs. Create it yourself, don't paste keys into the agent chat.
- Hackathon clusters end Fri Nov 13.

### Elasticsearch
- **Free Serverless trial, Elasticsearch project type:** https://ela.st/hack-kubecon
- Store the project's data in Elasticsearch; build via REST API/clients or **MCP**.
- Features to use: embeddings with **Jina** (part of the Cloud service), keyword/vector/time-series/geo queries, aggregations and dashboards, **Elastic Workflows** or **Agent Builder** (incl. MCP), **Elastic Agent Skills**.

---

## Before you arrive (official)
- Gitar, Dash0 and Radar Cloud accounts.
- Elasticsearch track: a Kubernetes cluster + Docker (cloud, or local kind/k3d/minikube).
- Radar track: just a GitHub account and a coding agent.
- Laptop + charger.

---

## What this means for us (our read, not official)

1. **Start the submission repo fresh after 11:00.** Best fit: create it from the Radar starter template (public, Argo CD wired, team cluster) and build features there through Gitar PRs. Use this repo's code/docs only as reference and research.
2. **Make the repo public** and keep a README with setup instructions.
3. **Add an "AI disclosure" section to the README** (Codex, DeepSeek subagents, Claude Code), and make sure every teammate can explain the architecture.
4. **Instrument with OTel in the first hour** and connect Dash0 + Radar MCP to the agent before writing features.
5. **One small PR per feature all day**, with `.gitar/review/` rules; break CI once on purpose for the auto-apply story.
6. **Collect demo evidence as you go:** Radar Checks before/after, timeline, a shared investigation; a Dash0 Agent0 root-cause + fix PR; a health dashboard/SLO; Gitar review + auto-apply on a real PR.
7. **Elasticsearch must be the main database**, with hybrid search (BM25 + Jina embeddings via `semantic_text`, fused with RRF).
8. **Lean into accessibility** for Merge Forward (Deaf/HoH, neurodiversity).
9. Stop building ~5:00 to rehearse; submit before 5:30.
