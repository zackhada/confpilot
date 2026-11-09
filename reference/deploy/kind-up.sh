#!/usr/bin/env bash
# kind-up.sh — stand up ConfPilot on a local kind cluster.
#
#   1. create a kind cluster (name overridable via CLUSTER_NAME)
#   2. build the FastAPI image from the repo root (../app)
#   3. load the image into the cluster
#   4. apply the kustomize manifests into namespace `confpilot`
#   5. print status / rollout info
#
# Usage:
#   ./deploy/kind-up.sh
#   CLUSTER_NAME=confpilot IMAGE=confpilot-api:latest ./deploy/kind-up.sh
#
# Prereqs: docker, kubectl. `kind` is auto-installed if missing (brew or binary).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/deploy"
CLUSTER_NAME="${CLUSTER_NAME:-confpilot}"
IMAGE="${IMAGE:-confpilot-api:latest}"

log() { printf '\033[1;34m[kind-up]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[kind-up]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker  >/dev/null 2>&1 || die "docker is required but not installed."
command -v kubectl >/dev/null 2>&1 || die "kubectl is required but not installed."

# --- ensure kind ------------------------------------------------------------
if ! command -v kind >/dev/null 2>&1; then
  log "kind not found — installing..."
  if command -v brew >/dev/null 2>&1; then
    brew install kind
  else
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    case "$os" in
      darwin) os="darwin" ;; linux) os="linux" ;; *) die "unsupported OS: $os" ;;
    esac
    arch="$(uname -m)"
    case "$arch" in
      x86_64) arch="amd64" ;; aarch64|arm64) arch="arm64" ;; *) die "unsupported arch: $arch" ;;
    esac
    curl -Lo /usr/local/bin/kind "https://kind.sigs.k8s.io/dl/v0.27.0/kind-${os}-${arch}"
    chmod +x /usr/local/bin/kind
  fi
fi

# --- create cluster ---------------------------------------------------------
if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  log "kind cluster '$CLUSTER_NAME' already exists — reusing."
else
  log "creating kind cluster '$CLUSTER_NAME'..."
  kind create cluster --name "$CLUSTER_NAME"
fi
kubectl config use-context "kind-$CLUSTER_NAME" >/dev/null 2>&1 || true

# --- build + load image -----------------------------------------------------
if [[ ! -f "$REPO_ROOT/app/requirements.txt" || ! -f "$REPO_ROOT/app/main.py" ]]; then
  die "expected ../app/{main.py,requirements.txt} (the FastAPI app) — build the app agent's code first."
fi

log "building image '$IMAGE' from repo root..."
docker build -t "$IMAGE" -f "$DEPLOY_DIR/Dockerfile" "$REPO_ROOT"

log "loading '$IMAGE' into kind..."
kind load docker-image "$IMAGE" --name "$CLUSTER_NAME"

# --- apply manifests --------------------------------------------------------
# kubectl >= 1.14 renders kustomize natively via -k.
log "applying kustomize manifests (namespace: confpilot)..."
kubectl apply -k "$DEPLOY_DIR"

# --- status ---------------------------------------------------------------
log "waiting for api rollout (best effort)..."
kubectl -n confpilot rollout status deployment/api --timeout=180s || true

log "namespace objects:"
kubectl -n confpilot get all

echo
log "done. Next steps:"
echo "  # port-forward the API"
echo "  kubectl -n confpilot port-forward svc/api 8000:8000"
echo "  # install Radar (UI + MCP + AI investigation)"
echo "  ./deploy/install-radar.sh"
echo "  # note: embed-worker is intentionally OOMKilled; fix with:"
echo "  kubectl apply -k $DEPLOY_DIR/overlays/oom-fix"
