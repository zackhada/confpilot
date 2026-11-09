# Dash0 (observability) — Track 2, $4,000

**What it is:** an OpenTelemetry-native observability platform: traces, logs, metrics, real-user monitoring (RUM) in one place, plus **Agent0**, an AI SRE you can ask "why is this slow?".

**What judges want**
1. Deep instrumentation: traces, logs, metrics, and RUM on the frontend.
2. Agent0 or the Dash0 MCP server used to find and fix something **real** during the day — shown in the demo.
3. Observability is part of the product, not bolted on.
4. Bonus: a dashboard or SLO showing app health.

## Setup (~15 min)
1. Sign up at https://app.dash0.com (14-day trial).
2. Pick the data region — **it can't be changed later.** For Salt Lake City use **AWS US West (Oregon) `us-west-2`**.
3. Settings → Auth Tokens: create two tokens
   - **backend** token (ingest traces/metrics/logs)
   - **RUM** token: ingest-only, website dataset (it ships in browser code, so it's public)
4. Copy the exact OTLP endpoint from Settings → Endpoints (shows a ready cURL snippet).

## Wire up the app
The API exports traces, metrics and logs over OTLP/HTTP ([`api/confpilot/telemetry.py`](../../api/confpilot/telemetry.py)); the `es/` layer adds `es.*` spans ([`es/confpilot_es/telemetry.py`](../../es/confpilot_es/telemetry.py)). Set in `.env`:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://ingress.us-west-2.aws.dash0.com:4318   # confirm in Settings → Endpoints
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <backend token>,Dash0-Dataset=default"
OTEL_SERVICE_NAME=confpilot-api
```
On Kubernetes the pod reads the endpoint and service name from the `app-config` ConfigMap and the headers from the `app-credentials` Secret, and exports straight to Dash0 (see [`deploy/README.md`](../../deploy/README.md)).
Frontend RUM: [`web/src/telemetry/dash0.ts`](../../web/src/telemetry/dash0.ts) uses the Dash0 web SDK. Set `VITE_DASH0_RUM_TOKEN` and `VITE_DASH0_RUM_ENDPOINT` at build time; with either unset, browser monitoring is off.

The key signal is the `confpilot.card.word_to_card_ms` histogram, recorded under the `card.push` span in [`api/confpilot/routes/ws.py`](../../api/confpilot/routes/ws.py). The dashboard "confpilot-word-to-card" is kept as code in `observability/dash0/`, and the SLO is 95% of cards within 800 ms.

## MCP — let your coding agent read live telemetry
Endpoint format: `https://api.<region>.<cloud>.dash0.com/mcp` → ours: `https://api.us-west-2.aws.dash0.com/mcp`
```bash
# Codex (documented by Dash0)
codex mcp add dash0 --url https://api.us-west-2.aws.dash0.com/mcp
codex mcp login dash0

# Claude Code
claude mcp add --transport http --scope user dash0 https://api.us-west-2.aws.dash0.com/mcp
# then /mcp → dash0 → sign in
```

## Demo moment
Show the word-to-card dashboard and SLO during the live demo. Nothing is broken on purpose (see `AGENTS.md`); ask Agent0 about real latency or errors only.

Sources: https://www.dash0.com/docs/dash0/ai/mcp · https://www.dash0.com/docs/dash0/get-started · https://www.dash0.com/docs/dash0/miscellaneous/glossary/auth-tokens
