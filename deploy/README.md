# Deploy

ConfPilot runs as one image (FastAPI plus the built phone app) on the `confpilot` EKS
cluster: account 045129524740, `us-east-1`, AWS CLI profile `hackathon-team`. Our AWS role
cannot create IAM roles or OIDC providers, and we have no DNS name yet, so public HTTPS comes
from a Cloudflare quick tunnel and images live on GHCR.

Commands are PowerShell, run from the repo root.

| Path | What it is |
| --- | --- |
| `eks/cluster.yaml` | eksctl config for the cluster |
| `Dockerfile`, `Dockerfile.dockerignore` | The image. Build context is the repo root |
| `k8s/` | Kustomize manifests: namespace, config, Deployment, Service, tunnel, CI identity |
| `hello/` | The same manifests with a public placeholder image |
| `tunnel-url.ps1` | Prints the current public URL |
| `rollout.ps1` | Rolls an image tag out from a laptop |
| `make-deployer-kubeconfig.ps1` | Builds the kubeconfig for the `KUBE_CONFIG` repo secret |
| `../.github/workflows/deploy.yml` | Builds, pushes and rolls out on every merge to `main` |
| `../.github/workflows/deploy-check.yml` | On pull requests: kubeconform on the manifests, image build and a `/healthz` probe |

## From an empty cluster to a public URL

### 1. Cluster and kubectl

```powershell
aws sso login --profile hackathon-team
eksctl create cluster -f deploy/eks/cluster.yaml --profile hackathon-team   # once, about 15 min
aws eks update-kubeconfig --name confpilot --region us-east-1 --profile hackathon-team
kubectl get nodes   # two Ready nodes; with none, every pod stays Pending
```

### 2. Hello over HTTPS (no image and no secrets needed)

```powershell
kubectl apply -k deploy/hello
deploy/tunnel-url.ps1 -Wait      # prints https://<random-words>.trycloudflare.com
```

Open the URL on a phone. `/healthz` returns 200, and `wss://<host>/echo` echoes WebSocket
frames, which proves the path the app needs.

The placeholder (`traefik/whoami`) is a debug server on a public URL: it prints its own
environment to anyone who asks. The overlay gives it no config and no secrets, and CI checks
that. Keep it that way, and swap the real app in (step 4) before creating `app-credentials`.

### 3. Image pull secret (a human runs this; only while the GHCR package is private)

Use a GitHub token with the `read:packages` scope (`gh auth refresh -s read:packages` adds it
to the gh token):

```powershell
kubectl -n confpilot create secret docker-registry ghcr-pull --docker-server=ghcr.io --docker-username=<github-user> --docker-password=$(gh auth token)
```

Once the package is public this Secret is unnecessary, and a missing one is ignored. A package
does not become public when the repo does: change it under Package settings > Change visibility.

### 4. The real app

Every merge to `main` makes the Deploy workflow push `ghcr.io/zackhada/confpilot:<sha>` and
`:main`. The image builds whether or not `web/` and `es/` are on `main` yet; without `web/`
it is the API alone and `/` returns 404. Then:

```powershell
kubectl apply -k deploy/k8s      # swaps the placeholder for ghcr.io/zackhada/confpilot:main
kubectl -n confpilot rollout status deployment/confpilot
deploy/tunnel-url.ps1            # the URL is unchanged: the tunnel pod was not touched
```

This `apply` is the only way off the placeholder. `rollout.ps1` and the Deploy workflow only
change the image tag, and the placeholder's pod spec cannot run the real image.

### 5. App credentials (a human runs this; values never go in a file in the repo)

**Create `app-credentials` only after step 4, when the real image is running. Never while the
placeholder is.** Check first:

```powershell
kubectl -n confpilot get deployment confpilot -o jsonpath='{.spec.template.spec.containers[0].image}'   # must be ghcr.io/zackhada/confpilot:...
```

Put these keys in a file outside the repo, one `KEY=value` per line, with no quotes:

| Key | Value |
| --- | --- |
| `SESSION_SECRET` | A random string, made once and kept, so sessions survive a restart |
| `ES_URL`, `ES_API_KEY` | The Elastic Cloud Serverless project |
| `DEEPGRAM_API_KEY` | Speech-to-text |
| `LLM_API_KEY` | The definer and the probe |
| `OTEL_EXPORTER_OTLP_HEADERS` | `Authorization=Bearer <dash0 token>,Dash0-Dataset=default` |

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"    # a value for SESSION_SECRET
kubectl -n confpilot create secret generic app-credentials --from-env-file=$HOME\confpilot-credentials.env
kubectl -n confpilot rollout restart deployment/confpilot   # the pod reads the Secret at start
```

The Secret is `optional` in the Deployment, so the app starts without it and picks it up on
the restart. To go back to the placeholder later, delete the Secret first.

### 6. Deploy on merge (repo admin, once)

The workflow rolls out only if the `KUBE_CONFIG` repo secret exists. Without it the workflow
still pushes the image and succeeds.

```powershell
deploy/make-deployer-kubeconfig.ps1      # writes $env:TEMP\confpilot-deployer.kubeconfig
Get-Content -Raw $env:TEMP\confpilot-deployer.kubeconfig | gh secret set KUBE_CONFIG --repo zackhada/confpilot
Remove-Item $env:TEMP\confpilot-deployer.kubeconfig
```

Setting the secret needs repo admin. If the admin is on another machine, they can paste the
file content at Settings > Secrets and variables > Actions > New repository secret.

The identity behind it is the `deployer` ServiceAccount (`k8s/deployer-rbac.yaml`). It can
patch the `confpilot` Deployment and watch the rollout, and nothing else. Patching a
Deployment does let it choose the image the pod runs, so treat the secret as a deploy key.
Revoke it with `kubectl -n confpilot delete secret deployer-token`.

## Roll out by hand

```powershell
deploy/rollout.ps1 <commit-sha>   # an image the Deploy workflow pushed
deploy/rollout.ps1 main           # re-pull the moving tag
deploy/rollout.ps1 -Undo          # back to the previous revision
```

`kubectl apply -k deploy/k8s` resets the image to `:main`. Use it for config changes and
`rollout.ps1` for releases.

To check the image locally before a merge:

```powershell
docker build --platform linux/amd64 -f deploy/Dockerfile -t confpilot:dev .
docker run --rm -p 8000:8000 --read-only --tmpfs /tmp confpilot:dev   # http://localhost:8000/healthz
```

The image mirrors the repo: `/app/api` (working directory, with the virtualenv), `/app/es`,
`/app/content/glossary.json` (`GLOSSARY_PATH`) and `/app/static` (`STATIC_DIR`, the built
`web/`). It starts `uvicorn confpilot.main:app` as uid 10001. Only `api/`, `web/`, `es/`,
`contracts/` and `content/glossary.json` enter the build context; to add another path,
allow it in `Dockerfile.dockerignore` and copy it in the Dockerfile.

Non-secret settings are the `configMapGenerator` entries in `k8s/kustomization.yaml`. The
generated ConfigMap's name carries a hash of its content, so changing a value and running
`kubectl apply -k deploy/k8s` rolls the pod; old ConfigMaps are left behind and can be
deleted. `ALLOWED_ORIGINS` is empty because the phone app is served from the API's own origin.

## One replica, and what a release costs

The room hub is in memory, so the API is exactly one replica: never scale it, never add an
HPA. Releases use `RollingUpdate` with `maxSurge: 1, maxUnavailable: 0`. The old pod serves
until the new one passes `/healthz`, then it is stopped, its WebSockets close, and phones
reconnect to the new pod within a couple of seconds. `Recreate` would mean no pod at all for
the whole image pull and startup (15 to 40 seconds), and no pod for good if the new image is
broken. The cost of the surge is a second or two where both pods exist; the old one is
already being stopped, so the room ends up on one hub. In-memory room state does not survive
a release either way.

## The public URL

`k8s/cloudflared.yaml` runs `cloudflared tunnel --url http://confpilot:80`. Cloudflare gives
it a random `https://*.trycloudflare.com` name with a real certificate. WebSockets work.
Limits to know:

- **The URL changes when the cloudflared pod restarts** (node replacement, eviction, a
  `rollout restart`, an edit to `cloudflared.yaml`). App releases do not touch it. After any
  restart run `deploy/tunnel-url.ps1` and regenerate QR codes.
- Quick tunnels have no uptime guarantee, cap concurrent requests at 200, and do not support
  server-sent events. We use WebSockets only.
- The pod needs outbound access to Cloudflare on UDP or TCP 7844 and TCP 443.

### Stable URL (upgrade path, not done)

1. **Named Cloudflare tunnel.** Needs a Cloudflare account and a domain on it. Create the
   tunnel in the Zero Trust dashboard, store its token in a Secret, and change the args in
   `cloudflared.yaml` to `tunnel --no-autoupdate run` with `TUNNEL_TOKEN` from that Secret.
   Nothing changes in AWS.
2. **AWS load balancer with an ACM certificate.** Needs a DNS name such as
   `confpilot.skylersmith.me`. Request a certificate in ACM (DNS validation), make the
   Service `type: LoadBalancer` on port 443 (target port `http`) with these annotations, and
   point a CNAME at the load balancer:

   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-type: nlb
   service.beta.kubernetes.io/aws-load-balancer-ssl-cert: <certificate ARN>
   service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
   ```

   The cloud controller that EKS already runs creates the load balancer, so this does not
   need the AWS Load Balancer Controller or a new IAM role. Ask for a Network Load Balancer
   as above: a Classic ELB with an HTTPS listener does not pass WebSockets. The app pings
   every 20 seconds, well inside the NLB's 350 second idle timeout. Untested here, and it
   creates AWS resources (a load balancer and a certificate).

## Dash0 operator (documented, not installed)

The operator is a cluster-wide Helm install, so Clayton runs it. It needs `helm`
(`winget install Helm.Helm`). Dash0's onboarding screen prints this command with our region
and token filled in; use that copy if it differs.

```powershell
kubectl create namespace dash0-system
kubectl -n dash0-system create secret generic dash0-authorization-secret --from-literal=token=<dash0 auth token>
helm repo add dash0-operator https://dash0hq.github.io/dash0-operator
helm repo update dash0-operator
helm upgrade --install dash0-operator dash0-operator/dash0-operator --namespace dash0-system `
  --set operator.dash0Export.enabled=true `
  --set operator.dash0Export.endpoint=<ingress endpoint from Dash0 Settings, port 4317> `
  --set operator.dash0Export.secretRef.name=dash0-authorization-secret `
  --set operator.dash0Export.secretRef.key=token `
  --set operator.clusterName=confpilot
```

Then turn monitoring on for our namespace by applying a `Dash0Monitoring` resource in
`confpilot` (the onboarding screen gives the exact `apiVersion`). The operator collects pod
logs and Kubernetes metrics, and restarts the Deployment once to inject auto-instrumentation.
That restart is a normal surge rollout.

Where it meets our manifests:

- The app's own OTel SDK reads `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` and
  `OTEL_RESOURCE_ATTRIBUTES` from the `app-config` ConfigMap and `OTEL_EXPORTER_OTLP_HEADERS`
  from `app-credentials`, so traces reach Dash0 directly even without the operator.
- The endpoint in `k8s/kustomization.yaml` is our Dash0 region, us-west-2
  (`https://ingress.us-west-2.aws.dash0.com:4318`).
- The pod has a read-only root filesystem and only `/tmp` writable.

## Radar (documented, not connected)

- **Local, read-only, no install in the cluster:** `kubectl radar` opens the UI at
  `http://localhost:9280` against the current kubectl context. Agents connect with
  `claude mcp add --transport http radar http://localhost:9280/mcp-readonly`. AI
  investigations need Radar running on the laptop like this.
- **Radar Cloud:** in the Cloud Native Hackathon org, the connect-a-cluster flow gives the
  install command for its in-cluster agent. It is a cluster-wide install, so Clayton runs it
  (we have not seen the command, so it is not copied here). Agents use
  `claude mcp add --scope user radar-cloud --transport http https://api.radarhq.io/mcp` and
  must pass our cluster id on every call.
- Every workload here carries `app.kubernetes.io/name`, `component` and `part-of` labels, so
  Radar's topology groups the API, the tunnel and the CI identity under `confpilot`.
- Take the "before" screenshot of Checks as soon as the cluster is connected.

## Plan B: the Radar team vcluster

If EKS is not usable, the same image runs on the hackathon vcluster from
`https://join.cnh.radarhq.io`. There, Argo CD syncs a folder of this repo from `main` into the
namespace `team-<team>`, and the platform routes `https://<team>.cnh.radarhq.io` to a Service
named `app` on port 80. The repo and the GHCR package must both be public. The Dockerfile and
the image need no change. In the manifests:

| Ours today | On the vcluster |
| --- | --- |
| `namespace: confpilot` on every resource, plus `namespace.yaml` | Remove `namespace.yaml`; set `namespace: team-<team>` once in the kustomization |
| Service `confpilot` | Rename to `app`, or add a second Service `app` with the same selector, port 80 |
| `cloudflared.yaml` and `tunnel-url.ps1` | Remove; the platform provides HTTPS |
| `deployer-rbac.yaml`, `KUBE_CONFIG`, `rollout.ps1`, the workflow's rollout job | Remove. Argo CD self-heals, so `kubectl set image` is reverted |
| Image tag set by `kubectl set image` | Tag lives in git: the workflow commits `images[].newTag` in the kustomization, as the starter's workflow does. That needs `contents: write` and a way past the branch protection on `main` |
| `imagePullSecrets: ghcr-pull` | Not needed once the package is public; harmless if left |
| `app-credentials` Secret in `confpilot` | Same name, created by a human in `team-<team>` |
| Applied with `kubectl apply -k deploy/k8s` | An Argo CD `Application` (project `team-<team>`, path `deploy/k8s`, `targetRevision: main`), modelled on `argocd/application.yaml` in `skyhook-io/cnh-starter` |

Unchanged: one replica, the surge rollout, probes on `/healthz`, port 8000, resources, labels.
Not verified: the idle timeout of the platform's gateway for WebSockets. The app's 20 second
ping should keep sockets open.

## Notes

- ECR: `aws ecr describe-repositories` works for our role and returns no repositories. We
  have not tried to create one. Nodes could pull from ECR through `HackathonEKSNodeRole`, but
  GitHub Actions has no way to push there without an OIDC provider or long-lived keys, so
  GHCR stays the registry.
- `kubectl delete -k deploy/k8s` removes everything, because it deletes the namespace: the
  app, the tunnel (the public URL is gone for good), `app-credentials` and `ghcr-pull`. To
  stop only the app, use `kubectl -n confpilot scale deployment/confpilot --replicas=0`; the
  next `kubectl apply -k deploy/k8s` brings it back.
- Delete the cluster when the event is over:
  `eksctl delete cluster -f deploy/eks/cluster.yaml --profile hackathon-team`.
