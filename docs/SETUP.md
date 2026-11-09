# SETUP.md — TONIGHT checklist (Sun Nov 8, 2026)

> **Start here:** the per-product setup guides are in [setup/](setup/README.md). This file is the original long-form research.

Everything you must create/install **tonight** so tomorrow morning is pure feature-building.
Do these in order. Each section is copy-paste runnable. Time estimate per section is in the header.

Legend:
- ✅ = verified against vendor docs today
- ⚠️ = UNVERIFIED / needs a live click tonight (exact UI labels or exact token/URL may differ — write down what you actually see)

---

## 0. Common prerequisites (5 min)

Verify these are already on the machine (we'll need all four vendors + the app):

```bash
git --version            # ✅ needed for everything
docker --version         # ✅ kind cluster + optional local Elastic
python3 --version        # ✅ FastAPI backend (app/)
node --version           # ✅ for @dash0/sdk-web / mcp-remote
kubectl version --client # ✅ Radar + deploy/
helm version --short     # ✅ Radar in-cluster + deploy
claude --version         # ✅ Claude Code for Radar + Dash0 MCP servers
kind version             # ⚠️ if missing: brew install kind  (https://kind.sigs.k8s.io/)
```

Create the GitHub repo for ConfPilot **now** and push the PLAN.md skeleton so Gitar has something to connect to:

```bash
# (do this in the existing project dir /Users/zackhada/Desktop/cnh-hackathon)
git init -b main
git remote add origin git@github.com:<YOU>/cnh-confpilot.git   # ⚠️ create repo first
git add -A && git commit -m "Skeleton: PLAN.md, docs/" && git push -u origin main
```

> Source: vendor docs below. GitHub repo creation is your own step (⚠️ adapt to your account).

---

## 1. Gitar — install GitHub app, review instructions, rules, CI diagnosis, auto-apply (~20 min)

> Note: Gitar is now part of **Sonar** (gitar.ai redirects to sonarsource.com/products/gitar). Docs live at docs.gitar.ai and still describe the Gitar product. ✅ https://www.sonarsource.com/products/gitar/

### 1.1 Create account + install the GitHub App

1. Go to **https://app.gitar.ai/sign-up** and sign in with **GitHub**. ✅ https://docs.gitar.ai/quickstart
   - Free **14-day trial, no credit card**. ✅ https://docs.gitar.ai/quickstart
2. **Start the GitHub install from inside Gitar**, not from the GitHub Marketplace:
   - In Gitar: **Settings → Configuration → Connect (GitHub)**. ✅ https://docs.gitar.ai/connecting-code/github
   - ⚠️ PITFALL (documented): installing the app from GitHub while signed OUT of Gitar leaves it installed but unconnected. If that happens: uninstall at GitHub **Settings → Installed GitHub Apps → Gitar → Uninstall**, then redo from Gitar. ✅ https://docs.gitar.ai/connecting-code/github#troubleshooting
3. On GitHub, select the org and grant access to **the ConfPilot repo only** (or all repos — your call).
4. Approve the two permission sets Gitar requires (both read+write):
   - **Code, Issues, Pull Requests** (analyze, create/manage PRs, push commits)
   - **Actions, Checks, Commit statuses, Workflows** (read CI logs, diagnose failures, fix) ✅ https://docs.gitar.ai/connecting-code/github#permissions
5. Back in Gitar, confirm the repo shows under **Connected Repositories**.

### 1.2 Commit the Gitar config into the repo

Use the files in this `docs/` folder tonight (they are the authoritative drafts):

```bash
mkdir -p .gitar/review .gitar/rules .gitar/config
cp docs/GITAR_RULES.md .gitar/review/confpilot.md      # review instructions
# (GITAR_RULES.md also contains a .gitar/rules/ file + apply.md — see its "split these" section)
git add .gitar && git commit -m "Gitar review instructions + rules" && git push
```

Key facts (so you know what the files do) — ✅ https://docs.gitar.ai/configuration/repository-config:
- `.gitar/review/*.md` → custom code-review instructions (what Gitar looks for)
- `.gitar/rules/*.md` → natural-language automation workflows (YAML frontmatter: `title`, `when`, `actions`, `type`)
- `.gitar/config/apply.md` → per-repo auto-apply criteria
- `.gitar/instructions/*.md` → instructions read by *every* Gitar agent (not only review)
- Gitar also auto-reads `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.claude/rules/*`. ✅

### 1.3 Configure CI failure diagnosis + auto-apply

1. **CI failure diagnosis needs no extra connection for GitHub Actions** — Gitar reads Actions logs using the GitHub App credential. ✅ https://docs.gitar.ai/features/ci-failure-analysis#which-ci-platforms-need-connecting
   - (Only Jenkins/CircleCI/Concourse/Woodpecker/Buildkite/TeamCity/Harness/Bitrise need a separate connect step — we use GitHub Actions, so skip.)
2. In **Settings → Configuration → Behavior**: ✅ https://docs.gitar.ai/configuration/settings
   - Turn ON **Retry unrelated CI failures** (auto-retries flaky/unrelated failures) — independent of auto-apply.
   - Turn ON **Auto-apply** criteria: set **Organization review criteria** to something like
     `Only fix minor findings: unused imports, formatting, lint, type errors, and failing tests. Skip auth, payment, and DB migration logic.`
   - ⚠️ Verify tonight whether **auto-apply** is included on the trial plan — the marketing page says auto-apply is on **Pro and Enterprise**. ✅ https://www.sonarsource.com/products/gitar/ ("Fixes applied autonomously … where your team turns on auto-apply (Pro and Enterprise)"). If the trial caps it, use the per-PR command `gitar auto-apply:on` and confirm it arms.
3. Per-repo criteria (committed, versioned): `.gitar/config/apply.md` (see GITAR_RULES.md).

### 1.4 Commands cheat-sheet (post as PR comments)

| Want | Comment on the PR |
|---|---|
| Turn on auto-fix for this PR | `gitar auto-apply:on` |
| Turn off | `gitar auto-apply:off` |
| Ask for a fix | `gitar fix this` (or reply `fix` on an inline finding) |
| Show all rules + why skipped | `gitar display:verbose` |
| Dismiss blocking review | `gitar unblock` (must be enabled in Settings) |

✅ https://docs.gitar.ai/commands · labels: `gitar-managed` (enables auto-apply), `gitar-skip`, `gitar-approved` ✅ https://docs.gitar.ai/labels

---

## 2. Dash0 — trial, OTLP endpoint + auth token, Agent0, MCP for Claude Code (~20 min)

> Dash0 docs: https://www.dash0.com/docs/dash0 · pricing/trial: https://www.dash0.com/pricing

### 2.1 Create org + pick region (cannot change later)

1. Sign up at **https://app.dash0.com** (Google / GitHub / email). ✅ https://www.dash0.com/docs/dash0/get-started
   - **14 days free trial** ✅ https://www.dash0.com/pricing
2. Create the organization and choose the **data-storage region**.
   - ⚠️ Region is **immutable** after org creation — pick the same region for OTLP, API, and MCP. ✅ https://www.dash0.com/docs/dash0/get-started
   - Available regions (for endpoints): ✅ https://www.dash0.com/docs/dash0/ai/mcp

| Region | OTLP ingest | API / MCP |
|---|---|---|
| AWS Europe (Ireland) | `ingress.eu-west-1.aws.dash0.com` | `api.eu-west-1.aws.dash0.com` |
| AWS Europe (Frankfurt) | `ingress.eu-central-1.aws.dash0.com` | `api.eu-central-1.aws.dash0.com` |
| GCP Europe (Netherlands) | `ingress.europe-west4.gcp.dash0.com` | `api.europe-west4.gcp.dash0.com` |
| AWS US East (N. Virginia) | `ingress.us-east-1.aws.dash0.com` | `api.us-east-1.aws.dash0.com` |
| AWS US West (Oregon) | `ingress.us-west-2.aws.dash0.com` | `api.us-west-2.aws.dash0.com` |

> For SLC, **us-west-2.aws** (Oregon) is the natural pick. ✅ https://www.dash0.com/docs/dash0/ai/mcp

### 2.2 Create auth tokens

1. Go to **https://app.dash0.com/goto/settings/auth-tokens** (or Settings → Auth Tokens). ✅ https://www.dash0.com/docs/dash0/miscellaneous/glossary/auth-tokens
2. Tokens look like `auth_abc123...`. ✅ https://www.dash0.com/docs/dash0/miscellaneous/glossary/auth-tokens
3. Create **two** tokens and record them in a local secrets file (NOT in git):

```bash
mkdir -p .secrets && cat > .secrets/dash0.env <<'EOF'
# backend / collector (ingest traces+metrics+logs)
DASH0_AUTH_TOKEN=auth_REPLACE_BACKEND
DASH0_OTLP_URL=https://ingress.us-west-2.aws.dash0.com:4318
DASH0_API_URL=https://api.us-west-2.aws.dash0.com
DASH0_DATASET=default
# RUM (public — MUST be ingest-only on the website dataset)
DASH0_RUM_AUTH_TOKEN=auth_REPLACE_RUM
EOF
chmod 600 .secrets/dash0.env && echo ".secrets/" >> .gitignore
```

   - **Backend token**: allow all signal types (traces/metrics/logs), dataset = `default`.
   - **RUM token**: ⚠️ it will ship in the browser bundle, so restrict it to **Ingesting** only, on the **website dataset**, per Dash0's own guidance. ✅ https://www.dash0.com/docs/dash0/monitoring/websites/getting-started-website-monitoring

### 2.3 OTLP endpoint + headers (exact)

- OTLP/HTTP endpoint: `https://ingress.<region>.dash0.com:4318` (gRPC: `:4317`).
  - ⚠️ Confirm the exact URL/port tonight in the in-product endpoint reference: **https://app.dash0.com/goto/settings/endpoints?endpoint_type=otlp_http** (it shows a copy-paste cURL snippet with your URL + auth header). ✅ https://www.dash0.com/docs/dash0/miscellaneous/glossary/endpoints
- Auth header: `Authorization=Bearer <token>` and dataset: `Dash0-Dataset=default`. ✅ https://www.dash0.com/docs/dash0/opentelemetry/distributions/python/configuration

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://ingress.us-west-2.aws.dash0.com:4318"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer ${DASH0_AUTH_TOKEN},Dash0-Dataset=default"
```

- Dash0 Python OTel distribution (auto-instruments Flask/FastAPI/etc.): ✅ https://www.dash0.com/docs/dash0/opentelemetry/distributions/python/getting-started

```bash
pip install dash0-opentelemetry        # ✅ PyPI package (v0.3.3 at research time)
DASH0_OTEL_COLLECTOR_BASE_URL=https://ingress.us-west-2.aws.dash0.com:4318 \
  opentelemetry-instrument uvicorn app.main:app
```

### 2.4 Agent0 (their AI agent)

- Agent0 overview: https://www.dash0.com/docs/dash0/ai/agent0/overview
- It can query telemetry via MCP, generate dashboards/alerts, run **automations**, and be **delegated** tasks. ✅ https://www.dash0.com/docs/dash0/ai/agent0/overview/use-agent0/query-telemetry-via-mcp
- Tonight just confirm you can open Agent0 chat in the Dash0 UI and it lists your (still-empty) dataset. We exercise it live tomorrow on the "chaos" incident.

### 2.5 MCP server for Claude Code

Dash0 **hosts** the MCP server (streamable HTTP — nothing to install). ✅ https://www.dash0.com/docs/dash0/ai/mcp

Interactive OAuth (recommended, runs as *you*):

```bash
claude mcp add --transport http --scope user dash0 https://api.us-west-2.aws.dash0.com/mcp
```

Static auth token (CI/agent, runs at the token's permissions + default model):

```bash
claude mcp add --transport http dash0 https://api.us-west-2.aws.dash0.com/mcp \
  --header "Authorization: Bearer ${DASH0_AUTH_TOKEN}"
```

For Cursor / `mcpServers`-style clients, or local-only clients via `mcp-remote`, the exact JSON is in the docs — see ✅ https://www.dash0.com/docs/dash0/ai/mcp#connect-with-an-auth-token (and the `mcp-remote` npm bridge). Test it:

```bash
claude mcp list            # should show dash0
# in claude: "list the datasets I can see"  → expect listDatasets tool to answer
```

---

## 3. Radar by Skyhook — install, MCP for Claude Code, AI investigations (~15 min)

> Repo: https://github.com/skyhook-io/radar · Docs: https://radarhq.io/docs · Free forever, no account. ✅ (README)

### 3.1 Install the CLI/kubectl plugin

```bash
# Option A — quick installer (also sets up the `radar` shorthand)
curl -fsSL https://get.radarhq.io | sh

# Option B — Homebrew
brew install kubectl-radar

# Verify
kubectl radar --version
```

✅ https://github.com/skyhook-io/radar#installation (also Krew `kubectl krew install radar`, desktop app, and Helm for in-cluster).

### 3.2 Point it at a cluster

We need a k8s cluster tomorrow for the Radar track. Spin up kind tonight:

```bash
kind create cluster --name confpilot        # ⚠️ create once; keep it for tomorrow
kubectl cluster-info --context kind-confpilot
kubectl radar --context kind-confpilot      # opens http://localhost:9280
```

> Flags you'll want: `--port 9280` (default), `--timeline-storage=sqlite` (persist history), `--mcp-read-only` (disable write tools if you only want reads). ✅ https://github.com/skyhook-io/radar#usage

### 3.3 MCP server for Claude Code

MCP is **on by default** on the same port (9280). Read-only endpoint recommended: ✅ https://github.com/skyhook-io/radar#connect-your-agent

```bash
claude mcp add --transport http radar http://localhost:9280/mcp-readonly
```

- `/mcp-readonly` = read-only tools (diagnose, get_changes, list_resources, get_resource, logs, events).
- `/mcp` = adds **write** tools (restart, scale, apply, rollback, GitOps sync, node drain), marked destructive. ✅ https://github.com/skyhook-io/radar#ai-agents-mcp-server-and-ai-investigations
- Verify: `claude mcp list` → `radar`, then ask Claude "what's unhealthy in the kind-confpilot cluster?"

### 3.4 AI investigations (the "Radar AI investigation" judge criterion)

Run an investigation from a terminal or the **Investigate** button in the UI. Needs a supported agent CLI (Claude Code / Codex / Cursor / OpenCode) + MCP on + auth off. ✅ https://github.com/skyhook-io/radar#ai-investigations

```bash
radar diagnose deploy/<name> -n <ns>           # opens your agent on the failure
radar diagnose deploy/<name> -n <ns> --json > conclusion.json
```

Tomorrow we use this on a deliberately OOMKilled/CrashLoop workload (see PR_PLAN.md, PR #10).

### 3.5 In-cluster (Helm) — optional but good for the "run on k8s w/ Radar" criterion

```bash
helm repo add skyhook https://skyhook-io.github.io/helm-charts
helm install radar skyhook/radar -n radar --create-namespace
```

✅ https://github.com/skyhook-io/radar#in-cluster-deployment — ⚠️ note: in-cluster installs do NOT run AI investigations (investigations need the CLI + an agent on the machine running Radar). Keep the laptop `kubectl radar` for investigations.

---

## 4. Elastic — Cloud trial (or local) + inference endpoints for semantic_text (~20 min)

> semantic_text reference: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text (GA since 9.0). ✅

### 4.1 Option A — Elastic Cloud trial (recommended; Inference API "just works")

1. Sign up: **https://cloud.elastic.co/registration** (14-day free trial, **all features included**, no credit card). ✅ https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text ("Get started free 14-day free trial All features included")
2. Create a deployment (smallest size is fine). Record:

```bash
mkdir -p .secrets && cat > .secrets/elastic.env <<'EOF'
ES_ENDPOINT=https://<deployment-id>.es.<region>.aws.elastic-cloud.com
ES_API_KEY=<base64 api key>        # ⚠️ create under Security → API keys
EOF
chmod 600 .secrets/elastic.env && echo ".secrets/" >> .gitignore
```

   - ⚠️ The **Inference API requires an appropriate license** (Platinum/Enterprise/trial). The Cloud trial includes it. ✅ https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text

### 4.2 Option B — Local Elasticsearch (no cloud)

```bash
docker run -d --name es-confpilot -p 9200:9200 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  -e xpack.license.self_generated.type=trial \
  docker.elastic.co/elasticsearch/elasticsearch:9.0.0
```

- ⚠️ The `xpack.license.self_generated.type=trial` line is what turns on the trial license locally so the Inference API + `semantic_text` default endpoint work. Verify tonight with `curl localhost:9200/_xpack/license` → should show `trial`. (Elastic docs: https://www.elastic.co/guide/en/elasticsearch/reference/current/start-trial.html)

### 4.3 Verify inference endpoints for semantic_text

`semantic_text` **auto-creates / uses a default inference endpoint** when you omit `inference_id`. The default varies by deployment+version — this matters because you should pin one to keep embeddings consistent: ✅ https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text-setup-configuration

| Deployment | Default `inference_id` | Runs on |
|---|---|---|
| Elastic Cloud Hosted 9.4+ / Serverless | `.jina-embeddings-v5-text-small` | Elastic Inference Service (EIS) |
| Elastic Cloud Hosted 9.3 | `.elser-2-elastic` | EIS |
| Elastic Cloud Hosted 9.0–9.2 | `.elser-2-elasticsearch` | `elasticsearch` service |

**Tonight, pin it explicitly** (don't rely on the default) so index + query use the same model:

```bash
# check what inference endpoints exist / are deployable
curl -s -u elastic -H "Content-Type: application/json" \
  "$ES_ENDPOINT/_inference?pretty"           # ⚠️ adjust auth to match your setup

# create a smoke-test index with an explicit semantic_text inference_id
curl -s -u elastic -H "Content-Type: application/json" -XPUT "$ES_ENDPOINT/semantic-embeddings" -d '{
  "mappings": { "properties": { "content": { "type": "semantic_text",
      "inference_id": ".elser-2-elastic" } } }
}'
```

- `semantic_text` auto-configures sparse/dense vectors, generates embeddings at index time, and chunks long text — **no manual pipeline**. ✅ https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text
- ⚠️ On a fresh Cloud 9.4+ deployment the `inference_id` may need to be `.jina-embeddings-v5-text-small` (EIS) instead of `.elser-2-elastic` — **check `GET _inference` output and copy the exact id that exists**, then use it in PR #4. ✅ https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text-setup-configuration#use-default-endpoints

---

## 5. Final smoke test tonight (5 min)

Run this and confirm every vendor answers before you sleep:

```bash
# 1. Gitar: create a tiny PR (this README edit) and confirm the Gitar dashboard comment appears
# 2. Dash0: send one span
python3 - <<'PY'
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
import os
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(OTLPSpanExporter(
        endpoint=os.environ["DASH0_OTLP_URL"]+"/v1/traces",
        headers={"Authorization": "Bearer "+os.environ["DASH0_AUTH_TOKEN"]})))
with trace.get_tracer("smoke").start_as_current_span("tonight-smoke-test"):
    pass
print("sent")
PY
# 3. Radar: kubectl radar --context kind-confpilot  (UI loads; MCP /mcp-readonly reachable)
# 4. Elastic: the _inference call above returned endpoints
```

---

## 6. UNVERIFIED / flagged items (write down what you actually see tonight)

1. ⚠️ **Gitar auto-apply availability on the 14-day trial** — marketing says Pro/Enterprise. Confirm `gitar auto-apply:on` arms on a PR; if not, plan the live auto-apply demo around the exact plan tier you have. ✅ https://www.sonarsource.com/products/gitar/
2. ⚠️ **Dash0 exact OTLP URL/port** — copy from https://app.dash0.com/goto/settings/endpoints?endpoint_type=otlp_http (docs give `ingress.<region>.dash0.com`; standard OTLP/HTTP port is 4318). ✅ https://www.dash0.com/docs/dash0/miscellaneous/glossary/endpoints
3. ⚠️ **Elastic default inference id** — depends on Cloud stack version (9.4+ → `.jina-embeddings-v5-text-small`; 9.3 → `.elser-2-elastic`). Confirm via `GET _inference`. ✅ https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/semantic-text-setup-configuration#use-default-endpoints
4. ⚠️ **Dash0 RUM token scope** — must be Ingesting-only on the website dataset (it's public in the browser bundle). ✅ https://www.dash0.com/docs/dash0/monitoring/websites/getting-started-website-monitoring
5. ⚠️ **Local Elastic trial license** — `xpack.license.self_generated.type=trial`; verify `_xpack/license` reports `trial` or Inference API calls will fail. ✅ https://www.elastic.co/guide/en/elasticsearch/reference/current/start-trial.html
6. ⚠️ **Radar in-cluster vs laptop** — in-cluster (Helm) installs can't run AI investigations; use laptop `kubectl radar` for the investigation demo. ✅ https://github.com/skyhook-io/radar#ai-investigations
