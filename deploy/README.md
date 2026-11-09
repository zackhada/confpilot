# deploy/ — ConfPilot infrastructure

Kubernetes + container scaffolding for **ConfPilot**, the accessible AI
conference companion (see `../PLAN.md`). This directory contains everything
needed to run the FastAPI backend (`../app`) and its OpenTelemetry → Dash0
pipeline on a local kind cluster, plus a deliberately broken `embed-worker`
Deployment for the Radar AI-investigation demo.

## What's here

| Path | Purpose |
|------|---------|
| `Dockerfile` | Builds `../app` (context = repo root). `app/main.py` exposes `app`; served by `uvicorn main:app`. Runs as non-root uid/gid 10001. |
| `kustomization.yaml` | Root kustomization → `base/`. Apply with `kubectl apply -k deploy/`. |
| `base/` | All manifests (namespace `confpilot`, ConfigMap/Secret, api Deployment+Service, OpenTelemetry Collector, embed-worker). |
| `overlays/oom-fix/` | Fix overlay for the intentional embed-worker OOMKilled fault. |
| `kind-up.sh` | Creates a kind cluster, builds + loads the image, applies kustomize. |
| `install-radar.sh` | Installs Skyhook Radar in-cluster via Helm (per its GitHub README). |
| `.github-workflows-ci.yml` | GitHub Actions workflow (ruff + pytest + docker build). Copy to `.github/workflows/ci.yml`. |

## Layout

```
deploy/
├── Dockerfile
├── kustomization.yaml            # resources: [base/]
├── base/
│   ├── kustomization.yaml        # namespace: confpilot
│   ├── namespace.yaml
│   ├── configmap.yaml            # ES_URL, LLM_PROVIDER/MODEL, OTel endpoint, LOG_LEVEL
│   ├── secret.yaml               # LLM keys, ES_API_KEY, Dash0 token+endpoint (CHANGE_ME)
│   ├── api-deployment.yaml       # limits + liveness/readiness probes on /healthz
│   ├── api-service.yaml
│   ├── otel-collector-configmap.yaml   # receiver -> Dash0 OTLP/HTTP exporter
│   ├── otel-collector-deployment.yaml  # Dash0 creds injected from Secret via env
│   ├── otel-collector-service.yaml
│   └── embed-worker-deployment.yaml    # 32Mi memory limit (deliberately tight)
├── overlays/oom-fix/             # raise limit to 256Mi + batch 64 -> 8
├── kind-up.sh
├── install-radar.sh
└── .github-workflows-ci.yml
```

## Run it

Prereqs: `docker`, `kubectl` (kind is auto-installed by the script).

```bash
# 1. Cluster + build + load + apply
./deploy/kind-up.sh

# 2. Port-forward the API
kubectl -n confpilot port-forward svc/api 8000:8000
curl -s localhost:8000/healthz          # expect 200

# 3. Radar in-cluster (UI + MCP), via Helm
./deploy/install-radar.sh
kubectl -n radar port-forward svc/radar 9280:9280   # open http://localhost:9280
```

### OOMKilled demo (Radar AI investigation)

`base/embed-worker-deployment.yaml` caps the embed worker at **32Mi** memory —
far below what loading an embedding model needs — so the pod is OOMKilled and
CrashLoopBackOffs. That is the real issue for Radar to find:

```bash
kubectl -n confpilot get pods                         # embed-worker -> CrashLoopBackOff
kubectl -n confpilot describe pod -l app.kubernetes.io/name=embed-worker | grep -i oom

# Radar UI/MCP (in-cluster, after install-radar.sh + port-forward):
claude mcp add --transport http radar http://localhost:9280/mcp-readonly

# AI investigations need the LOCAL binary (in-cluster installs don't run them):
curl -fsSL https://get.radarhq.io | sh
radar diagnose deploy/embed-worker -n confpilot

# The fix overlay:
kubectl apply -k deploy/overlays/oom-fix
```

## Secrets & Dash0

`base/secret.yaml` is a **template** (all values `CHANGE_ME`). Fill in real
values before production (or inject via `kubectl create secret` / a secret
manager). The OpenTelemetry Collector reads `DASH0_OTLP_ENDPOINT` and
`DASH0_TOKEN` from that Secret and exports to Dash0 OTLP/HTTP with
`Authorization: Bearer <token>`.

Dash0 endpoint shape: `https://ingress.<region>.aws.dash0.com:4318` (OTLP/HTTP)
or `:4317` (OTLP/gRPC) — confirm the exact URL in your Dash0 org's **Endpoints
reference** (it fully resolves your region).

## CI

`.github-workflows-ci.yml` runs ruff (`check` + `format --check`), pytest, and a
docker build. Copy it into your repo:

```bash
mkdir -p .github/workflows && cp deploy/.github-workflows-ci.yml .github/workflows/ci.yml
```

## Notes & uncertainties

- **App must exist first**: `kind-up.sh` and `.github-workflows-ci.yml` assume `../app/main.py`
  (exposing `app`) and `../app/requirements.txt` (must include `fastapi` +
  `uvicorn`) already exist — they are owned by the `app/` agent.
- **embed-worker entrypoint**: the worker runs `python -m app.embed_worker`;
  adjust `command` in `base/embed-worker-deployment.yaml` if the app ships a
  different module path.
- **Radar install** (`install-radar.sh`) installs in-cluster via Helm per the
  upstream README (`helm repo add skyhook https://skyhook-io.github.io/helm-charts &&
  helm install radar skyhook/radar -n radar --create-namespace`). Chart
  version/value keys are not pinned here (check `helm show values skyhook/radar`).
  In-cluster Helm installs do **not** run AI investigations — use the local
  binary (`kubectl radar`) for the OOMKilled AI-investigation demo.
- **OTel Collector image** pinned to `otel/opentelemetry-collector-contrib:0.165.0`.
