#!/usr/bin/env bash
# install-radar.sh — install Skyhook Radar in-cluster via Helm, following the
# upstream GitHub README (https://github.com/skyhook-io/radar):
#
#     helm repo add skyhook https://skyhook-io.github.io/helm-charts
#     helm install radar skyhook/radar -n radar --create-namespace
#
# Usage:
#   ./deploy/install-radar.sh
#   RADAR_RELEASE=radar RADAR_NAMESPACE=radar ./deploy/install-radar.sh
#
# UNCERTAINTY / CAVEATS (also in README):
#   - Uses default chart values straight from the README. The chart name/version
#     and value keys (e.g. mcp.enabled, service.type) are NOT pinned here and may
#     drift upstream — review `helm show values skyhook/radar` before production.
#   - Per the README, in-cluster Helm installs do NOT run AI investigations
#     (those need a local agent CLI). For the OOMKilled AI-investigation demo,
#     run the local binary (`kubectl radar`) + MCP server pointed at kind instead.

set -euo pipefail

RELEASE_NAME="${RADAR_RELEASE:-radar}"
NAMESPACE="${RADAR_NAMESPACE:-radar}"
HELM_REPO_NAME="skyhook"
HELM_REPO_URL="https://skyhook-io.github.io/helm-charts"

log() { printf '\033[1;35m[radar]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[radar]\033[0m %s\n' "$*" >&2; exit 1; }

command -v kubectl >/dev/null 2>&1 || die "kubectl is required."
command -v helm >/dev/null 2>&1 || die "helm is required — install it: brew install helm"

log "adding Helm repo '$HELM_REPO_NAME' ($HELM_REPO_URL)"
helm repo add "$HELM_REPO_NAME" "$HELM_REPO_URL"
helm repo update "$HELM_REPO_NAME"

log "installing Radar release '$RELEASE_NAME' in namespace '$NAMESPACE'"
helm upgrade --install "$RELEASE_NAME" "$HELM_REPO_NAME/radar" \
  -n "$NAMESPACE" --create-namespace --wait --timeout 5m

log "waiting for the Radar rollout"
kubectl -n "$NAMESPACE" rollout status deployment/radar --timeout=180s

echo
log "Radar installed. Expose the UI + MCP server (port 9280) with:"
echo "  kubectl -n $NAMESPACE port-forward svc/radar 9280:9280"
echo "  open http://localhost:9280"
echo
echo "Connect an AI agent (read-only MCP):"
echo "  claude mcp add --transport http radar http://localhost:9280/mcp-readonly"
echo
echo "NOTE: in-cluster Helm installs do not run AI investigations. For the"
echo "OOMKilled embed-worker investigation demo, use the local binary instead:"
echo "  curl -fsSL https://get.radarhq.io | sh && kubectl radar"
