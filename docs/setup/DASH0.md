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
The app already exports traces, metrics and logs over OTLP/HTTP (`app/confpilot/telemetry.py`). Set in `.env`:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://ingress.us-west-2.aws.dash0.com:4318   # confirm in Settings → Endpoints
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <backend token>,Dash0-Dataset=default"
OTEL_SERVICE_NAME=confpilot-api
```
On Kubernetes the OTel Collector in `deploy/base/otel-collector-*.yaml` forwards to Dash0 using the token from the secret.
Frontend RUM: replace the Dash0 RUM placeholder in `app/static/index.html` with the snippet from Dash0's website-monitoring setup.

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
Hit `/api/chaos` to inject latency/errors → ask Agent0 "why did /api/search get slow?" → it points to the cause → fix it in a Gitar-reviewed PR. Show a dashboard/SLO for health.

Sources: https://www.dash0.com/docs/dash0/ai/mcp · https://www.dash0.com/docs/dash0/get-started · https://www.dash0.com/docs/dash0/miscellaneous/glossary/auth-tokens
