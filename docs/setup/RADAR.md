# Radar (Kubernetes UI + AI SRE) — Track 3, $4,000

**What it is:** Skyhook's free, open-source Kubernetes UI. Shows everything running in the cluster; its AI investigation hands a broken workload to your coding agent (Codex, Claude Code, Cursor, OpenCode) to find the root cause.

**What judges want**
1. The app runs on Kubernetes with Radar connected (their provided cluster/namespace, or ours).
2. Radar's UI **and MCP** used throughout building and operating.
3. Show how Radar helped you ship, troubleshoot or improve.
4. Radar AI investigation on a **real** issue in the running app — show findings and what you did.

## Install (no account needed)
```bash
brew install kubectl-radar          # or: curl -fsSL https://get.radarhq.io | sh
brew install kind helm
open -a Docker
```

## Cluster + app
```bash
deploy/kind-up.sh                    # kind cluster, builds + loads image, applies deploy/base
kubectl -n confpilot create secret generic confpilot-secrets \
  --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
kubectl radar                        # UI at http://localhost:9280
```
If organizers give us a cluster/namespace at kickoff, point `kubectl` at it instead of kind.

## MCP — let your coding agent see the cluster
Radar must be running (`kubectl radar`). Read-only endpoint is safest:
```bash
# Claude Code (documented in Radar README)
claude mcp add --transport http radar http://localhost:9280/mcp-readonly
# Codex — same URL; UNVERIFIED (Radar's README shows the Claude command; this mirrors Codex's --url syntax)
codex mcp add radar --url http://localhost:9280/mcp-readonly
```
`/mcp` (no `-readonly`) adds write tools: restart, scale, apply, rollback.

## AI investigation
```bash
radar diagnose deploy/embed-worker -n confpilot
radar diagnose deploy/embed-worker -n confpilot --json > conclusion.json
```
Requires: an agent CLI on the machine running Radar, MCP on, auth off. **Does not work from an in-cluster (Helm) install** — run Radar on the laptop.

## Demo moment
`embed-worker` has a deliberately tight memory limit → gets OOMKilled → Radar AI investigation finds it → apply the fix overlay (`kubectl apply -k deploy/overlays/oom-fix`) via a Gitar-reviewed PR.

Sources: https://github.com/skyhook-io/radar (Installation, Connect your agent, AI investigations)
