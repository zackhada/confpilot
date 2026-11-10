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
The app runs on the `confpilot` EKS cluster; [`deploy/README.md`](../../deploy/README.md) is the runbook.
Radar is installed in that cluster in the `radar` namespace (see "Use the in-cluster Radar" below).
`kubectl radar` (UI at http://localhost:9280) also works from a laptop against the current context.

## MCP — let your coding agent see the cluster
Radar must be running (`kubectl radar`). Read-only endpoint is safest:
```bash
# Claude Code (documented in Radar README)
claude mcp add --transport http radar http://localhost:9280/mcp-readonly
# Codex — same URL; UNVERIFIED (Radar's README shows the Claude command; this mirrors Codex's --url syntax)
codex mcp add radar --url http://localhost:9280/mcp-readonly
```
`/mcp` (no `-readonly`) adds write tools: restart, scale, apply, rollback.

## Use the in-cluster Radar from Codex (EKS)

This EKS-specific guide fills the gap between the local setup above and the team's EKS
installation: Radar runs in the cluster, while Codex runs on a developer's computer. The
Radar track requires using its UI and MCP, so a loopback-only port-forward provides access
without exposing Radar publicly.

The EKS install runs Radar inside the `radar` namespace. Its Kubernetes Service is
`ClusterIP`, so it has no public address. Use `kubectl port-forward` to make the Radar UI
and MCP endpoint available only on this computer. Keep the port-forward running while using
the UI or MCP.

### Start the tunnel

Run this in a dedicated terminal and leave it open:

```bash
kubectl --context confpilot-admin -n radar port-forward --address 127.0.0.1 service/radar 9281:9280
```

The command should print `Forwarding from 127.0.0.1:9281 -> 9280`. Open
<http://localhost:9281> for the Radar UI. To check that the UI responds:

```bash
curl -fsS -o /dev/null -w 'Radar HTTP %{http_code}\n' http://127.0.0.1:9281/
```

This requires a valid `confpilot-admin` kubeconfig context and permission to port-forward
pods in the `radar` namespace. If your context has a different name, replace
`confpilot-admin` in the command. Check the current context with
`kubectl config current-context`.

### Connect Codex to the read-only MCP

Configure the Codex MCP server once, using the local tunnel URL:

```bash
codex mcp add radar --url http://localhost:9281/mcp-readonly
codex mcp list
```

If `radar` is already listed, keep its URL set to
`http://localhost:9281/mcp-readonly` instead of adding a duplicate. Reload or restart Codex
after changing MCP configuration so the tools appear in the session. The `/mcp-readonly`
endpoint is intentional; `/mcp` exposes write-capable tools.

### Agent checklist

Before querying the cluster, an agent should:

1. Read this Radar setup guide.
2. Confirm the port-forward terminal is still running, or start the command above.
3. Confirm `codex mcp list` shows `radar` enabled at
   `http://localhost:9281/mcp-readonly`.
4. Use the Radar MCP tools to make read-only queries. Do not assume access if the `radar`
   tools are absent from the current session; reload Codex after starting or configuring the
   server.

### If the connection stops

The tunnel is a local `kubectl` process, not a permanent cluster resource. It stops if the
terminal/process exits, the computer sleeps or loses network, AWS/Kubernetes credentials
expire, or the Radar pod is replaced. When it stops, the UI and MCP URL stop responding;
restart the port-forward command. A deployment of another app does not normally affect this
tunnel unless it also changes Radar, its pod, or the cluster connection. For regular personal
use, keeping the dedicated terminal open and restarting the command when needed is simplest.

Keep Radar private: do not bind the tunnel to `0.0.0.0` or create a public ingress just to
make the local MCP work.

## AI investigation
```bash
radar diagnose deploy/confpilot -n confpilot
radar diagnose deploy/confpilot -n confpilot --json > conclusion.json
```
Requires: an agent CLI on the machine running Radar, MCP on, auth off. **Does not work from an in-cluster (Helm) install** — run Radar on the laptop.

## Demo moment
Show the `confpilot` workloads, their health and events in Radar. Investigate only real issues; nothing is broken on purpose (see `AGENTS.md`).

Sources: https://github.com/skyhook-io/radar (Installation, Connect your agent, AI investigations)
