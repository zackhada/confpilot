#!/usr/bin/env python3
"""
Deterministic generator for the CloudNative Summit SLC 2026 dataset.

Produces:
  - talks.json      (~150 talks)  — fields: id, title, abstract, speakers,
                      track, room, start_time (ISO8601, America/Denver = -07:00
                      MST in November), level, tags
  - attendees.json  (~60 attendees) — fields: id, name, role, company, interests

Run:  python3 generate_data.py
The output is fully deterministic (fixed seed) so the files can be regenerated
or committed as-is. No network access is required.
"""

import json
import random
from pathlib import Path

random.seed(20261109)

# ---------------------------------------------------------------------------
# Conference schedule model
# ---------------------------------------------------------------------------
# 10 parallel tracks, one room each. Every track has 15 talks. Talks 0..7 of a
# track run on Day 1 (Mon 2026-11-09), talks 8..14 run on Day 2 (Tue 2026-11-10).
# America/Denver is on MST (UTC-07:00) in November, so the ISO8601 offset is -07:00.
SLOT_TIMES_DAY1 = ["09:00", "10:15", "11:30", "13:00", "14:15", "15:30", "16:45", "18:00"]
SLOT_TIMES_DAY2 = ["09:00", "10:15", "11:30", "13:00", "14:15", "15:30", "16:45"]
DAY1 = "2026-11-09"
DAY2 = "2026-11-10"

TRACK_ROOMS = {
    "Kubernetes": "Ballroom A",
    "eBPF & Kernel": "Room 250",
    "Security": "Room 251",
    "Observability": "Room 255",
    "AI Infrastructure": "Ballroom B",
    "Platform Engineering": "Ballroom C",
    "Networking": "Room 355",
    "Serverless & Edge": "Room 155",
    "Developer Experience": "Room 253",
    "Data & Streaming": "The Loft",
}

# ---------------------------------------------------------------------------
# Speaker name pool (talks)
# ---------------------------------------------------------------------------
SPEAKERS = [
    "Priya Sharma", "Marcus Chen", "Elena Rodriguez", "James Okafor", "Aiko Tanaka",
    "David Kim", "Sofia Almeida", "Liam O'Brien", "Nadia Hassan", "Tom Becker",
    "Rachel Nguyen", "Andre Silva", "Grace Liu", "Victor Mensah", "Ines Costa",
    "Sam Whitfield", "Fatima Zahra", "Jonas Weber", "Mei Lin", "Carlos Delgado",
    "Hannah Park", "Omar Farouk", "Isabelle Martin", "Ravi Patel", "Chloe Dubois",
    "Erik Johansson", "Lina Al-Rashid", "Ben Carter", "Yuki Sato", "Amara Osei",
    "Peter Novak", "Julia Fernandez", "Noah Stein", "Camille Laurent", "Dara Okafor",
    "Mateo Rossi", "Anika Berg", "Kwame Mensah", "Sana Iqbal", "Tobias Klein",
    "Leila Haddad", "Finn Andersen", "Zara Ahmed", "Diego Morales", "Ingrid Larsen",
    "Arjun Mehta", "Bianca Rossi", "Chen Wei", "Dalia Nasser", "Emeka Obi",
    "Farah Khan", "Gabriel Santos", "Helena Varga", "Ivan Petrov", "Jade Wu",
    "Kenji Nakamura", "Lucia Ferrara", "Miguel Torres", "Nora Eide", "Owen Gallagher",
    "Petra Horak", "Quinn O'Rourke", "Rita Sousa", "Stefan Bauer", "Talia Cohen",
    "Umar Syed", "Vera Ivanova", "Will Park", "Ximena Ruiz", "Yusuf Ali",
    "Zoe Martin", "Adrian Lupu", "Becca Holt", "Cesar Vega", "Dina Khalil",
]

# ---------------------------------------------------------------------------
# Talks: (title, abstract, track, level, [tags])
# 15 talks per track * 10 tracks = 150 talks
# ---------------------------------------------------------------------------
TALKS = [
    # ========================= Kubernetes (Ballroom A) =========================
    ("Scaling Kubernetes to 50,000 Nodes Without Losing Your Mind",
     "A deep dive into the control-plane bottlenecks that appear past a few thousand nodes. We cover etcd tuning, kube-apiserver sharding, and the operator changes that keep API latency flat as your fleet grows tenfold.",
     "Kubernetes", "Advanced", ["kubernetes", "scaling", "etcd", "control plane", "performance"]),
    ("The Cluster Autoscaler Is Dead, Long Live Karpenter",
     "Karpenter provisions nodes in seconds and right-sizes them to the pod, not the other way around. This talk compares autoscaling strategies and shows a live migration from cluster-autoscaler to Karpenter.",
     "Kubernetes", "Intermediate", ["kubernetes", "karpenter", "autoscaling", "cost optimization", "aws"]),
    ("Multi-Cluster Service Mesh: A Field Guide",
     "One mesh is hard, many meshes are harder. We walk through the architectural patterns for connecting Istio and Linkerd across clusters and clouds, including east-west gateways and identity federation.",
     "Kubernetes", "Advanced", ["kubernetes", "service mesh", "istio", "linkerd", "multi-cluster"]),
    ("Kubernetes Networking Demystified: From kube-proxy to Cilium",
     "Follow a packet from pod to service and out to the internet. We unpack CNI plugins, iptables vs eBPF data paths, and why Cilium's identity-based model changes what network policies can express.",
     "Kubernetes", "Intermediate", ["kubernetes", "networking", "cilium", "cnI", "kube-proxy"]),
    ("Scheduling 101: Why Your Pods Land Where They Do",
     "The scheduler is the silent arbiter of your cluster's health. Learn how filtering and scoring really work, and how to bend them with node affinity, topology spread, and custom scheduler plugins.",
     "Kubernetes", "Beginner", ["kubernetes", "scheduling", "affinity", "topology spread", "operators"]),
    ("GitOps at Scale: Argo CD, Flux, and the Road to Full Automation",
     "Two leading GitOps engines, two philosophies. We compare Argo CD and Flux on multi-tenancy, drift detection, and progressive delivery, then share the patterns that survive 100+ clusters.",
     "Kubernetes", "Intermediate", ["kubernetes", "gitops", "argo cd", "flux", "ci/cd"]),
    ("Operator Patterns: Building Controllers That Don't Break Production",
     "Writing a controller is easy; writing a controller that handles crashes, upgrades, and thousands of CRs is not. We cover status conditions, finalizers, leader election, and the reconciliation anti-patterns to avoid.",
     "Kubernetes", "Advanced", ["kubernetes", "operators", "controllers", "crd", "go"]),
    ("Hardening Your Cluster: Kubernetes Security Best Practices",
     "From pod security admission to seccomp profiles, a practical checklist for locking down a cluster without slowing down developers. Includes the CIS benchmark highlights that actually matter.",
     "Kubernetes", "Intermediate", ["kubernetes", "security", "pod security", "cis benchmark", "rbac"]),
    ("Windows Containers on Kubernetes in 2026",
     "Windows workloads are no longer second-class citizens. We cover HostProcess containers, gMSA identity, and the networking quirks that still bite teams running mixed Linux/Windows clusters.",
     "Kubernetes", "Intermediate", ["kubernetes", "windows", "containers", "gmsa", "networking"]),
    ("eBPF-Based CNI: Cilium in Production",
     "Cilium replaces kube-proxy with an eBPF data plane that gives you L7 policies and Hubble visibility. We share a production rollout story: what broke, what got faster, and what we'd do differently.",
     "Kubernetes", "Advanced", ["kubernetes", "cilium", "ebpf", "networking", "observability"]),
    ("Right-Sizing: Stop Paying for Idle CPU",
     "Most clusters run at 15% utilization because requests are set to guesses. Learn request/limit tuning strategies, Vertical Pod Autoscaler, and how to safely reclaim waste without risking OOMKilled.",
     "Kubernetes", "Intermediate", ["kubernetes", "cost optimization", "vpa", "resources", "finops"]),
    ("Stateful Workloads on Kubernetes: Databases Are People Too",
     "Running Postgres and Kafka on Kubernetes stopped being scary. We cover storage classes, PVC resizing, topology-aware scheduling, and the operator landscape that makes stateful day-2 ops survivable.",
     "Kubernetes", "Intermediate", ["kubernetes", "statefulsets", "databases", "storage", "operators"]),
    ("CRDs Gone Wild: API Design for Platform Teams",
     "Custom resources are your platform's public API. We discuss versioning, conversion webhooks, validation, and the naming/field conventions that keep a thousand CRDs from becoming unmaintainable.",
     "Kubernetes", "Advanced", ["kubernetes", "crd", "api design", "platform engineering", "versioning"]),
    ("Kubernetes on the Edge: K3s and Friends",
     "Running full Kubernetes on a Raspberry Pi or a thousand retail stores is a solved problem. We compare K3s, K0s, and MicroK8s and cover the fleet-management patterns for disconnected environments.",
     "Kubernetes", "Beginner", ["kubernetes", "edge", "k3s", "k0s", "iot"]),
    ("Upgrade Strategies: Zero-Downtime Cluster Version Bumps",
     "Version skew is the silent killer of cluster upgrades. We demonstrate a blue/green node pool strategy, feature-gate planning, and how to validate add-ons before the API server ever changes version.",
     "Kubernetes", "Advanced", ["kubernetes", "upgrades", "zero downtime", "version skew", "operations"]),

    # ========================= eBPF & Kernel (Room 250) =========================
    ("eBPF 101: From BPF to Production Observability",
     "A gentle introduction to extended Berkeley Packet Filter. We explain what eBPF is, how the verifier keeps you safe, and why it became the substrate for modern observability, networking, and security.",
     "eBPF & Kernel", "Beginner", ["ebpf", "kernel", "observability", "verifier", "linux"]),
    ("Writing Your First eBPF Program in 2026",
     "Live coding session: write, load, and inspect a real eBPF program with libbpf and BPF CO-RE. You will leave with a working tracer and a mental model of maps, helpers, and hooks.",
     "eBPF & Kernel", "Beginner", ["ebpf", "libbpf", "c", "co-re", "tracing"]),
    ("Cilium vs Calico: The eBPF Showdown",
     "Both claim the modern CNI crown. We benchmark data-plane throughput, policy capabilities, and observability to help you pick the right tool for your cluster size and security posture.",
     "eBPF & Kernel", "Intermediate", ["ebpf", "cilium", "calico", "networking", "benchmarks"]),
    ("Falco and Runtime Security with eBPF",
     "Falco watches syscalls to detect anomalous behavior in real time. We explain how its eBPF probe works, how to write rules that don't drown you in alerts, and how to respond automatically.",
     "eBPF & Kernel", "Intermediate", ["ebpf", "falco", "security", "runtime detection", "syscalls"]),
    ("BPF CO-RE: Write Once, Run Everywhere",
     "Compile-once-run-everywhere was the breakthrough that made eBPF portable. We explain BTF, CO-RE relocations, and how to ship a single object file across kernel versions and distros.",
     "eBPF & Kernel", "Advanced", ["ebpf", "co-re", "btf", "portability", "libbpf"]),
    ("eBPF for Load Balancing: Replacing kube-proxy",
     "kube-proxy's iptables rules don't scale to huge services. We show how eBPF-based load balancers use hash maps and socket operations to push throughput up while cutting tail latency.",
     "eBPF & Kernel", "Advanced", ["ebpf", "load balancing", "kube-proxy", "performance", "networking"]),
    ("Debugging the Kernel with bpftrace",
     "bpftrace is the awk of kernel tracing. We demo one-liners that answer 'why is this process slow?' and show how to script complex multi-probe investigations without kernel expertise.",
     "eBPF & Kernel", "Beginner", ["ebpf", "bpftrace", "debugging", "tracing", "performance"]),
    ("eBPF Security Risks: When the Tool Becomes the Attack Surface",
     "The same power that makes eBPF useful makes it dangerous. We analyze real CVEs, privilege-escalation paths, and the kernel-side mitigations that keep unprivileged eBPF from becoming a backdoor.",
     "eBPF & Kernel", "Advanced", ["ebpf", "security", "vulnerabilities", "kernel", "privilege escalation"]),
    ("Tetragon: Runtime Enforcement at Scale",
     "Tetragon goes beyond detection to enforce policy with eBPF, down to individual syscalls and file accesses. We demo real-time enforcement and the design trade-offs of blocking vs auditing.",
     "eBPF & Kernel", "Advanced", ["ebpf", "tetragon", "cilium", "enforcement", "security"]),
    ("eBPF and AI: Accelerating Inference in the Kernel",
     "Can eBPF make your ML serving faster? We explore filtering and in-kernel pre-processing that removes work before it ever reaches the GPU, plus the risks of moving logic into the kernel.",
     "eBPF & Kernel", "Advanced", ["ebpf", "ai", "gpu", "inference", "performance"]),
    ("Performance Analysis with eBPF: A Deep Dive",
     "CPU flame graphs, off-CPU time, and block I/O latency all from eBPF. We work through a real incident where eBPF data pointed to a fix that dashboards and logs completely missed.",
     "eBPF & Kernel", "Intermediate", ["ebpf", "performance", "flame graphs", "profiling", "sre"]),
    ("Pixie: Instant Kubernetes Observability",
     "Pixie gives you scriptable, per-request Kubernetes telemetry with zero manual instrumentation. We show how its eBPF-based protocol tracing works and how to query it like a database.",
     "eBPF & Kernel", "Intermediate", ["ebpf", "pixie", "observability", "kubernetes", "tracing"]),
    ("The Future of eBPF: What's Next After 1.0",
     "eBPF has conquered networking and observability; what's next? We look at arena maps, improved loops, kernel module replacement, and the standardization work shaping the next five years.",
     "eBPF & Kernel", "Intermediate", ["ebpf", "roadmap", "kernel", "linux", "community"]),
    ("eBPF Offload to SmartNICs",
     "When the kernel isn't fast enough, push eBPF onto the NIC. We cover XDP offload, SmartNIC programming models, and the real-world results from offloading DDoS filtering to hardware.",
     "eBPF & Kernel", "Advanced", ["ebpf", "xdp", "smartnic", "hardware offload", "networking"]),
    ("Tracing Microservices with eBPF and OpenTelemetry",
     "eBPF auto-instruments what OpenTelemetry can't reach. We combine the two to get end-to-end traces across legacy and modern services, and discuss when each approach wins.",
     "eBPF & Kernel", "Intermediate", ["ebpf", "opentelemetry", "tracing", "microservices", "observability"]),

    # ========================= Security (Room 251) =========================
    ("Zero Trust in Kubernetes: Beyond the Buzzword",
     "Zero trust is an architecture, not a product. We map the principles of least privilege, continuous verification, and micro-segmentation onto concrete Kubernetes primitives you can deploy today.",
     "Security", "Intermediate", ["security", "zero trust", "kubernetes", "least privilege", "segmentation"]),
    ("Supply Chain Security: SBOMs, SLSA, and Sigstore",
     "Your build pipeline is the new attack surface. We explain software bills of materials, the SLSA framework levels, and how Sigstore's keyless signing verifies provenance without a PKI nightmare.",
     "Security", "Intermediate", ["security", "supply chain", "sbom", "slsa", "sigstore"]),
    ("Policy as Code: OPA, Kyverno, and Gatekeeper Compared",
     "Three ways to enforce policy on Kubernetes, three very different ergonomics. We compare the policy languages, performance at scale, and the operational burden of each approach.",
     "Security", "Intermediate", ["security", "policy as code", "opa", "kyverno", "gatekeeper"]),
    ("Secrets Management: Vault, SOPS, and External Secrets",
     "Secrets in git, env vars, and config maps are all liabilities. We compare HashiCorp Vault, SOPS with age, and External Secrets Operator for delivering secrets to workloads safely.",
     "Security", "Intermediate", ["security", "secrets", "vault", "sops", "external secrets"]),
    ("Runtime Threat Detection with Falco",
     "Static scanning won't catch an attacker already inside. We show how Falco's eBPF probes detect shells, crypto miners, and exfiltration in real time, and how to wire alerts into your incident response.",
     "Security", "Intermediate", ["security", "falco", "ebpf", "threat detection", "incident response"]),
    ("Container Image Scanning Done Right",
     "Scanning every image in CI sounds great until the scanner adds 20 minutes to every build. We share a layered scanning strategy: base images, CI gates, registry admission, and runtime inventory.",
     "Security", "Intermediate", ["security", "containers", "image scanning", "vulnerabilities", "ci/cd"]),
    ("mTLS Everywhere: SPIFFE/SPIRE in Production",
     "Service-to-service encryption and identity are table stakes now. We walk through rolling out SPIFFE/SPIRE for workload identity, rotating certs, and the gotchas that emerge at scale.",
     "Security", "Advanced", ["security", "mtls", "spiffe", "spire", "identity"]),
    ("Kubernetes RBAC: Least Privilege That Works",
     "RBAC policies either block everything or allow everything. We show a practical methodology for role design, testing access with impersonation, and auditing who can actually do what.",
     "Security", "Intermediate", ["security", "rbac", "kubernetes", "access control", "audit"]),
    ("Supply Chain Attacks: The XZ Utils Post-Mortem",
     "The XZ Utils backdoor was the wake-up call the industry needed. We dissect how it happened, why it nearly shipped, and the structural changes to open-source maintenance it should force.",
     "Security", "Beginner", ["security", "supply chain", "xz utils", "open source", "incident"]),
    ("eBPF-Powered Security: A Practical Guide",
     "eBPF gives security tools kernel-level visibility without kernel modules. We survey the ecosystem — Falco, Tetragon, Tracee — and show how to choose and tune them for your threat model.",
     "Security", "Intermediate", ["security", "ebpf", "falco", "tetragon", "tracee"]),
    ("Cloud Security Posture Management in 2026",
     "Misconfigured buckets and open security groups remain the top cloud breach causes. We review the CSPM landscape and how to turn thousands of findings into a prioritized, fixable backlog.",
     "Security", "Beginner", ["security", "cspm", "cloud", "compliance", "misconfiguration"]),
    ("Secrets in CI/CD: Leak Prevention",
     "Every secret eventually ends up in a log line. We cover pre-commit hooks, secret scanning in pipelines, and the remediation workflow that makes a leaked secret a minor annoyance, not a breach.",
     "Security", "Intermediate", ["security", "ci/cd", "secret scanning", "pre-commit", "remediation"]),
    ("Identity for Workloads: SPIFFE Deep Dive",
     "How does a pod prove who it is to a database it has never met? We go deep on the SPIFFE spec, the SPIRE server/agent architecture, and federation across clusters and clouds.",
     "Security", "Advanced", ["security", "spiffe", "spire", "identity", "federation"]),
    ("Pentesting Kubernetes: An Attacker's View",
     "Red teaming a cluster reveals where defenses actually fail. We walk through a realistic attack chain — exposed dashboard to cluster-admin — and the detections that would have stopped it.",
     "Security", "Advanced", ["security", "pentesting", "red team", "attack chain", "kubernetes"]),
    ("Security Chaos Engineering: Breaking Things to Fix Them",
     "You don't know if your security controls work until you attack yourself. We show how to run safe security chaos experiments that validate detections, response runbooks, and failover.",
     "Security", "Advanced", ["security", "chaos engineering", "resilience", "testing", "detection"]),

    # ========================= Observability (Room 255) =========================
    ("OpenTelemetry: The Road to Standardized Observability",
     "OpenTelemetry is now the de facto standard for telemetry. We cover the current state of the spec, what's stable vs experimental, and how to adopt it without boiling the ocean.",
     "Observability", "Beginner", ["observability", "opentelemetry", "traces", "metrics", "logs"]),
    ("The Three Pillars Are Dead: Metrics, Logs, Traces Converge",
     "Treating metrics, logs, and traces as separate systems is a relic. We explore unified telemetry, exemplars, and the tools that let you jump from a metric spike to the exact log line and trace.",
     "Observability", "Intermediate", ["observability", "metrics", "logs", "traces", "telemetry"]),
    ("Prometheus at Scale: Cardinality Is the Enemy",
     "Prometheus is easy until your label cardinality explodes. We explain how cardinality kills memory and query performance, and share the design rules and recording rules that keep it healthy.",
     "Observability", "Advanced", ["observability", "prometheus", "cardinality", "metrics", "performance"]),
    ("eBPF-Based Observability: Zero Instrumentation",
     "What if you could get golden signals without touching application code? We show how eBPF produces request-level RED metrics and traces for any workload, including legacy monoliths.",
     "Observability", "Intermediate", ["observability", "ebpf", "zero instrumentation", "golden signals", "traces"]),
    ("Distributed Tracing in Microservices: A Practical Guide",
     "Tracing is easy to start and hard to make useful. We cover sampling strategies, context propagation pitfalls, and how to turn trace data into answers during an incident instead of a pretty graph.",
     "Observability", "Intermediate", ["observability", "tracing", "microservices", "sampling", "context propagation"]),
    ("SLOs That Matter: Error Budgets in Practice",
     "Most SLOs are vanity metrics. We show how to pick service-level indicators users actually feel, set error budgets teams respect, and use burn-rate alerts to balance velocity and reliability.",
     "Observability", "Intermediate", ["observability", "slo", "sli", "error budget", "sre"]),
    ("Grafana + Mimir: Massive Metric Storage",
     "When a single Prometheus can't hold your metrics, Mimir shards them horizontally. We cover the architecture, long-term retention, and the migration path from a pile of Prometheus servers.",
     "Observability", "Advanced", ["observability", "grafana", "mimir", "prometheus", "storage"]),
    ("Profiling in Production: Continuous Profiling with Parca",
     "CPU and memory profiles from production reveal waste that dashboards hide. We demo continuous profiling with Parca and show how a 15-minute profile session cut a service's CPU by 40%.",
     "Observability", "Intermediate", ["observability", "profiling", "parca", "performance", "cpu"]),
    ("Observability for LLM Applications",
     "LLM apps fail in new and confusing ways. We cover tracing model calls, token usage, latency breakdowns, and evals, plus the OTel GenAI conventions that are standardizing it all.",
     "Observability", "Intermediate", ["observability", "llm", "ai", "genai", "tracing"]),
    ("Alert Fatigue: Building Alerts People Actually Respond To",
     "If every alert wakes someone up, soon none do. We share the rubric for high-signal alerting — symptom-based, page-worthy, and actionable — and how to measure and reduce alert noise.",
     "Observability", "Beginner", ["observability", "alerting", "sre", "on-call", "incident response"]),
    ("The Cost of Observability: Cutting Your Bill by 70%",
     "Observability can quietly become your largest cloud line item. We break down where the money goes — ingestion, retention, cardinality — and the concrete steps that slashed our bill.",
     "Observability", "Intermediate", ["observability", "cost optimization", "finops", "retention", "sampling"]),
    ("Frontend Observability: RUM and Core Web Vitals",
     "Your users experience the frontend, so instrument it. We cover Real User Monitoring, Core Web Vitals, session replay ethics, and connecting a slow button click to the backend trace.",
     "Observability", "Intermediate", ["observability", "rum", "frontend", "core web vitals", "user experience"]),
    ("Logs Are Data Too: Structured Logging at Scale",
     "Unstructured logs are where information goes to die. We argue for structured logging, show ingestion pipelines that parse once and index well, and demonstrate log-based metrics that replace brittle dashboards.",
     "Observability", "Beginner", ["observability", "logging", "structured logging", "pipelines", "metrics"]),
    ("Dashboards Are Dead, Long Live Notebooks",
     "Static dashboards can't keep up with dynamic systems. We demo investigative workflows with notebooks and query builders that turn on-call engineers into detectives instead of dashboard-watchers.",
     "Observability", "Beginner", ["observability", "dashboards", "notebooks", "investigation", "sre"]),
    ("AI-Powered Root Cause Analysis: Agent0 and Friends",
     "AI agents are starting to triage incidents: correlating traces, logs, and metrics to propose root causes. We demo an agent-driven investigation and discuss where the tech works — and where it still lies.",
     "Observability", "Intermediate", ["observability", "ai", "root cause analysis", "agents", "incident response"]),

    # ========================= AI Infrastructure (Ballroom B) =========================
    ("Kubernetes for LLMs: Scheduling GPU Workloads",
     "GPUs are scarce and expensive, and Kubernetes was not built for them. We cover GPU-aware scheduling, topology, device plugins, and the patterns that keep expensive accelerators busy.",
     "AI Infrastructure", "Intermediate", ["ai", "kubernetes", "gpu", "llm", "scheduling"]),
    ("GPU Sharing and Fractional GPUs in K8s",
     "Not every workload needs a whole A100. We compare time-slicing, MIG, and MPS for sharing GPUs, and measure the throughput and isolation trade-offs of each approach.",
     "AI Infrastructure", "Advanced", ["ai", "gpu", "mig", "mps", "kubernetes"]),
    ("Serving LLMs at Scale: vLLM, TGI, and Beyond",
     "Serving a 70B model to thousands of users is an infrastructure problem. We benchmark vLLM, Text Generation Inference, and SGLang on throughput, latency, and memory efficiency.",
     "AI Infrastructure", "Advanced", ["ai", "llm", "vllm", "serving", "inference"]),
    ("Training Large Models on Kubernetes: A Case Study",
     "Training a large model is 30% modeling and 70% keeping a GPU fleet alive. We share a real training run: checkpointing, fault tolerance, and the networking that makes all-reduce tolerable.",
     "AI Infrastructure", "Advanced", ["ai", "training", "kubernetes", "gpu", "distributed training"]),
    ("Vector Databases for RAG: Choosing Wisely",
     "Pinecone, Weaviate, Qdrant, Milvus, pgvector, Elasticsearch — the field is crowded. We lay out the decision framework: scale, filtering, hybrid search, and operational overhead.",
     "AI Infrastructure", "Intermediate", ["ai", "vector database", "rag", "embeddings", "elasticsearch"]),
    ("RAG in Production: Chunking, Embedding, Re-ranking",
     "Retrieval-augmented generation is easy to demo and hard to productionize. We cover chunking strategies, embedding model choice, hybrid retrieval, and the re-rankers that make answers actually good.",
     "AI Infrastructure", "Intermediate", ["ai", "rag", "embeddings", "reranking", "llm"]),
    ("MLOps on Kubernetes: Kubeflow and Friends",
     "Kubeflow, MLflow, Ray, and Flyte all want to run your ML on Kubernetes. We compare the platforms and share the architecture that keeps data scientists productive without ops chaos.",
     "AI Infrastructure", "Intermediate", ["ai", "mlops", "kubeflow", "mlflow", "ray"]),
    ("Fine-Tuning Open Models on a Budget",
     "You don't need a million-dollar cluster to fine-tune. We cover LoRA, QLoRA, and parameter-efficient methods, plus the open-weight models that punch above their size for niche tasks.",
     "AI Infrastructure", "Beginner", ["ai", "fine-tuning", "lora", "open source", "llm"]),
    ("Inference Optimization: Quantization and KV Caching",
     "The difference between 2 tokens/sec and 200 is engineering, not magic. We explain quantization formats, KV cache management, and batching strategies that multiply your serving throughput.",
     "AI Infrastructure", "Advanced", ["ai", "quantization", "kv cache", "inference", "optimization"]),
    ("Building AI Agents with Tool Use and Memory",
     "Agents that call APIs, query databases, and remember context are the next wave. We build one live, covering tool schemas, retry loops, and the memory architecture that keeps agents coherent.",
     "AI Infrastructure", "Intermediate", ["ai", "agents", "llm", "tool use", "memory"]),
    ("Model Registries and Artifact Management",
     "Where do models live between training and serving? We cover model registries, versioning, lineage, and the promotion workflow that stops 'which model is in prod?' from being a scary question.",
     "AI Infrastructure", "Beginner", ["ai", "mlops", "model registry", "versioning", "governance"]),
    ("Data Pipelines for ML: Feature Stores and More",
     "Model quality is a data problem first. We walk through feature stores, offline/online serving consistency, and the streaming pipelines that keep features fresh without training-serving skew.",
     "AI Infrastructure", "Intermediate", ["ai", "feature store", "data pipelines", "mlops", "streaming"]),
    ("AI Workload Scheduling with Volcano and Kueue",
     "Batch AI jobs don't fit the standard scheduler. We compare Volcano and Kueue for gang scheduling, queueing, and fair sharing, and show how to keep both training and serving happy.",
     "AI Infrastructure", "Advanced", ["ai", "volcano", "kueue", "scheduling", "kubernetes"]),
    ("Cost-Effective AI: Spot Instances for Training",
     "Spot instances can cut training costs by 70% if you can survive preemption. We share checkpointing patterns, graceful preemption handling, and the math on when spot actually pays off.",
     "AI Infrastructure", "Intermediate", ["ai", "spot instances", "cost optimization", "training", "checkpointing"]),
    ("Evaluating LLMs: Benchmarks, Evals, and Guardrails",
     "How do you know your model got better? We cover benchmark pitfalls, building task-specific evals, and guardrails that catch hallucinations and toxic output before your users do.",
     "AI Infrastructure", "Intermediate", ["ai", "llm", "evals", "benchmarks", "guardrails"]),

    # ========================= Platform Engineering (Ballroom C) =========================
    ("Platform Engineering 101: Building Your First IDP",
     "Internal developer platforms promise paved roads, but where do you start? We lay out a crawl-walk-run plan: golden paths first, self-service second, and the metrics to prove value.",
     "Platform Engineering", "Beginner", ["platform engineering", "idp", "golden paths", "self-service", "devops"]),
    ("Backstage: The Developer Portal That Scales",
     "Backstage is the Swiss Army knife of developer portals, but only if you tame its plugin sprawl. We share the catalog modeling, scaffolder templates, and plugin governance that make it stick.",
     "Platform Engineering", "Intermediate", ["platform engineering", "backstage", "developer portal", "catalog", "plugins"]),
    ("Golden Paths: Opinionated by Design",
     "Developers don't want 50 choices at 2am. We explain how to design golden paths that are opinionated enough to be safe but flexible enough to not drive teams to shadow IT.",
     "Platform Engineering", "Intermediate", ["platform engineering", "golden paths", "developer experience", "self-service", "standards"]),
    ("Internal Developer Platforms: Build vs Buy",
     "Humanitec, Qovery, Port, or roll your own? We compare the build-vs-buy decision with real cost numbers and the hidden maintenance burden of a homegrown platform.",
     "Platform Engineering", "Beginner", ["platform engineering", "idp", "build vs buy", "humanitec", "port"]),
    ("The Platform as a Product: Treating Devs as Customers",
     "Platform teams fail when they become ticket queues. We reframe the platform as a product with a roadmap, user research, and success metrics, and show how that changes everything.",
     "Platform Engineering", "Intermediate", ["platform engineering", "product management", "developer experience", "roadmap", "adoption"]),
    ("Self-Service Infrastructure with Terraform",
     "Terraform modules are the API of your cloud. We show how to build reusable, versioned modules and the self-service workflow that lets teams provision safely without opening tickets.",
     "Platform Engineering", "Intermediate", ["platform engineering", "terraform", "iac", "self-service", "modules"]),
    ("Paved Roads and Guardrails: Empowering Without Restricting",
     "How much freedom is too much? We cover the guardrail patterns — policies, defaults, budgets — that keep developers fast while preventing the disasters that made ops teams gate everything.",
     "Platform Engineering", "Intermediate", ["platform engineering", "guardrails", "policy", "developer experience", "governance"]),
    ("Developer Experience Metrics: DORA and Beyond",
     "Deploy frequency is nice, but is the inner loop fast? We cover DORA, SPACE, and flow metrics, and how to measure developer experience without turning engineers into surveilled metrics.",
     "Platform Engineering", "Intermediate", ["platform engineering", "dora", "metrics", "developer experience", "flow"]),
    ("Ephemeral Environments: Preview on Every PR",
     "Full preview environments per pull request used to be a dream. We show how to spin up namespaced, seeded environments on demand, and how they changed our review and QA culture.",
     "Platform Engineering", "Intermediate", ["platform engineering", "ephemeral environments", "preview", "kubernetes", "ci/cd"]),
    ("Cloud Cost Governance for Platform Teams",
     "Cost is now a platform concern, not a finance afterthought. We cover tagging, showback vs chargeback, anomaly detection, and the FinOps rituals that keep the CFO off your back.",
     "Platform Engineering", "Intermediate", ["platform engineering", "finops", "cost governance", "cloud", "tagging"]),
    ("Standardizing CI/CD Across 100 Teams",
     "A hundred teams, a hundred pipelines, zero consistency. We share how we built shared pipeline templates and reusable actions that gave teams speed without a big-bang migration.",
     "Platform Engineering", "Intermediate", ["platform engineering", "ci/cd", "pipelines", "standardization", "github actions"]),
    ("From DevOps to Platform Engineering: A Migration Story",
     "We didn't build a platform in a quarter; we evolved into one. This is the honest story of moving from a shared DevOps team to productized internal platforms, including the parts that failed.",
     "Platform Engineering", "Beginner", ["platform engineering", "devops", "migration", "organizational change", "lessons learned"]),
    ("Multi-Tenancy in Internal Platforms",
     "One platform, many tenants, no noisy neighbors. We cover namespace-level tenancy, quotas, and the isolation trade-offs between soft (namespace) and hard (cluster) tenancy.",
     "Platform Engineering", "Advanced", ["platform engineering", "multi-tenancy", "kubernetes", "quotas", "isolation"]),
    ("The Hidden Cost of Abstraction",
     "Every abstraction leaks, and platforms leak most of all. We catalog the debugging pain when things break beneath the platform, and how to design abstractions that fail loud instead of silently.",
     "Platform Engineering", "Advanced", ["platform engineering", "abstraction", "debugging", "operations", "design"]),
    ("Platform Teams: Organizational Anti-Patterns",
     "The wrong org structure can kill a great platform. We dissect the anti-patterns — the gatekeeper team, the invisible team, the fixer team — and the org designs that actually work.",
     "Platform Engineering", "Beginner", ["platform engineering", "organizations", "team topologies", "anti-patterns", "leadership"]),

    # ========================= Networking (Room 355) =========================
    ("Service Mesh Showdown: Istio vs Linkerd vs Cilium",
     "Three meshes, three philosophies. We benchmark mTLS overhead, control-plane resource use, and operational complexity, and give a decision guide for when each is the right call.",
     "Networking", "Intermediate", ["networking", "service mesh", "istio", "linkerd", "cilium"]),
    ("eBPF and the Future of Kubernetes Networking",
     "eBPF is eating the networking stack from kube-proxy to L7 policies. We explain the shift, what it unlocks for throughput and visibility, and the migration path for existing clusters.",
     "Networking", "Intermediate", ["networking", "ebpf", "kubernetes", "cilium", "performance"]),
    ("Gateway API: The Next Generation of Ingress",
     "Ingress was never enough; Gateway API is the fix. We cover the new resource model, HTTPRoute and GRPCRoute, and why Gateway API is becoming the standard across controllers.",
     "Networking", "Intermediate", ["networking", "gateway api", "ingress", "kubernetes", "httproute"]),
    ("BGP on Kubernetes: MetalLB and Cilium",
     "Sometimes your cluster needs to speak to the network like a router. We cover MetalLB and Cilium BGP modes, load-balancer announcements, and ECMP for on-prem and edge deployments.",
     "Networking", "Advanced", ["networking", "bgp", "metallb", "cilium", "load balancing"]),
    ("DNS in Kubernetes: CoreDNS Deep Dive",
     "Every outage is a DNS outage until proven otherwise. We trace service DNS resolution end to end, cover CoreDNS tuning, and debug the mysterious ndots:5 behavior that slows your apps.",
     "Networking", "Advanced", ["networking", "dns", "coredns", "kubernetes", "debugging"]),
    ("Load Balancing at Planet Scale",
     "From L4 to L7 and back again, load balancing gets weird at scale. We cover consistent hashing, direct server return, and the anycast and failover patterns behind global load balancers.",
     "Networking", "Advanced", ["networking", "load balancing", "anycast", "l7", "scale"]),
    ("Zero Trust Networking with Cilium",
     "Network policies built on IPs don't survive dynamic workloads. We show how Cilium's identity-based policies, L7 rules, and FQDN filtering deliver real zero-trust networking.",
     "Networking", "Advanced", ["networking", "cilium", "zero trust", "network policy", "identity"]),
    ("Multi-Cluster Networking: Submariner and Beyond",
     "Connecting clusters across clouds is still surprisingly hard. We compare Submariner, Cilium Cluster Mesh, and flat networks, and the service discovery and failover each enables.",
     "Networking", "Advanced", ["networking", "multi-cluster", "submariner", "cilium", "hybrid cloud"]),
    ("Network Policies That Actually Work",
     "Most network policies are either allow-all or deny-all. We show how to design tiered policies, use policy-as-code to generate them, and test them so they don't silently break services.",
     "Networking", "Intermediate", ["networking", "network policy", "kubernetes", "policy as code", "security"]),
    ("QUIC and HTTP/3 for Cloud Native Services",
     "HTTP/3 is here and your mesh may not be ready. We explain QUIC's benefits for latency and mobility, and the hurdles in load balancers, meshes, and observability tooling.",
     "Networking", "Advanced", ["networking", "quic", "http3", "protocols", "performance"]),
    ("Observability of the Network: Flow Logs and Hubble",
     "You can't debug what you can't see. We cover network flow observability with Hubble, eBPF flow logs, and how to answer 'why is this service talking to that IP?' in seconds.",
     "Networking", "Intermediate", ["networking", "observability", "hubble", "flow logs", "ebpf"]),
    ("Edge Networking: Global Anycast and CDNs",
     "Users are everywhere; your origin is not. We cover anycast, geo-DNS, edge compute, and the CDN patterns that keep latency low and availability high across continents.",
     "Networking", "Intermediate", ["networking", "edge", "anycast", "cdn", "latency"]),
    ("Encryption Everywhere: WireGuard and IPsec in K8s",
     "Node-to-node traffic is often plaintext. We compare WireGuard and IPsec for pod encryption, their performance costs, and how to enable transparent encryption without breaking the network.",
     "Networking", "Advanced", ["networking", "encryption", "wireguard", "ipsec", "security"]),
    ("Kubernetes Multi-Network: Multus and CNI Chaining",
     "Some workloads need multiple interfaces or SR-IOV performance. We cover Multus, CNI chaining, and the advanced networking use cases that demand more than one pod network.",
     "Networking", "Advanced", ["networking", "multus", "cni", "sr-iov", "kubernetes"]),
    ("Performance Tuning: The Cost of Your Mesh",
     "Sidecars add latency; how much is too much? We measure the overhead of popular meshes and show tuning — eBPF mode, ambient mesh, and protocol detection — that recovers lost throughput.",
     "Networking", "Advanced", ["networking", "service mesh", "performance", "ambient mesh", "latency"]),

    # ========================= Serverless & Edge (Room 155) =========================
    ("Serverless Kubernetes: Knative and OpenFaaS",
     "Serverless on Kubernetes gives you scale-to-zero without leaving your cluster. We compare Knative and OpenFaaS, and cover the cold-start and autoscaling behaviors you'll actually see.",
     "Serverless & Edge", "Intermediate", ["serverless", "knative", "openfaas", "kubernetes", "autoscaling"]),
    ("WebAssembly: The Next Serverless Runtime",
     "Wasm boots in microseconds and runs everywhere. We explain the component model, WASI, and why WebAssembly is poised to become the lingua franca of serverless and edge compute.",
     "Serverless & Edge", "Beginner", ["serverless", "webassembly", "wasm", "wasi", "edge"]),
    ("FaaS Cold Starts: Optimization Techniques",
     "Cold starts are the original serverless sin. We benchmark language runtimes, snapshot/restore, and keep-warm strategies, and show how to get function latency from seconds to milliseconds.",
     "Serverless & Edge", "Advanced", ["serverless", "cold start", "faas", "performance", "lambda"]),
    ("Event-Driven Architectures with Knative Eventing",
     "Loose coupling is the promise of event-driven systems. We build a Knative Eventing topology — brokers, triggers, sources — and discuss the delivery guarantees and dead-letter patterns.",
     "Serverless & Edge", "Intermediate", ["serverless", "knative", "event-driven", "eventing", "broker"]),
    ("Edge Computing: Running K8s at the Edge",
     "Edge sites have bad networks and no operators. We cover lightweight K8s distributions, GitOps for fleets, and the observability patterns that work when your cluster is in a wind farm.",
     "Serverless & Edge", "Intermediate", ["edge", "kubernetes", "k3s", "gitops", "fleet management"]),
    ("WebAssembly on Kubernetes: Spin and WasmEdge",
     "Run Wasm side by side with containers via runwasi and SpinKube. We demo cold start under a millisecond, smaller images, and the security model that makes Wasm a great neighbor.",
     "Serverless & Edge", "Intermediate", ["webassembly", "wasm", "kubernetes", "spin", "wasmedge"]),
    ("Serverless Data: Streaming with Kafka and Functions",
     "Functions + streams is a powerful combination. We show how to trigger functions from Kafka topics, handle backpressure, and build exactly-once-ish pipelines without a server in sight.",
     "Serverless & Edge", "Intermediate", ["serverless", "kafka", "streaming", "event-driven", "functions"]),
    ("Durable Execution: Temporal and Durable Functions",
     "Long-running workflows crash, retry, and wait for humans. Durable execution frameworks make that survivable. We compare Temporal and cloud durable functions and the saga patterns they enable.",
     "Serverless & Edge", "Intermediate", ["serverless", "temporal", "durable execution", "workflows", "sagas"]),
    ("The Serverless Database Problem",
     "Connections are the enemy of scale-to-zero. We cover serverless-friendly databases (Neon, PlanetScale, DynamoDB), HTTP-based SQL proxies, and connection pooling for bursty functions.",
     "Serverless & Edge", "Intermediate", ["serverless", "databases", "connection pooling", "neon", "dynamodb"]),
    ("IoT and Edge: From Sensors to Insights",
     "A million sensors generate a lot of messy data. We cover the ingestion, buffering, and edge analytics patterns that turn raw telemetry into decisions without drowning your cloud bill.",
     "Serverless & Edge", "Beginner", ["edge", "iot", "ingestion", "analytics", "mqtt"]),
    ("Cloudflare Workers vs Serverless Containers",
     "Two serverless worlds: isolate-based Workers and container-based FaaS. We compare cold starts, limits, and developer experience, and where each fits in a modern stack.",
     "Serverless & Edge", "Intermediate", ["serverless", "cloudflare workers", "containers", "edge", "comparison"]),
    ("WebAssembly Components: The WASI Revolution",
     "The component model makes Wasm composable across languages. We explain WIT interfaces, component linking, and what it means to write a library once and use it from any language.",
     "Serverless & Edge", "Intermediate", ["webassembly", "wasm", "wasi", "component model", "wit"]),
    ("Cost Optimization for Serverless: Stop Over-Provisioning",
     "Serverless pricing rewards the attentive and punishes the lazy. We cover right-sizing memory, the cost of idle warm functions, and the monitoring that catches runaway invocations.",
     "Serverless & Edge", "Beginner", ["serverless", "cost optimization", "finops", "aws lambda", "monitoring"]),
    ("Real-Time Apps at the Edge with WebSockets",
     "Real-time features push state to the edge. We cover WebSocket infrastructure, fan-out with Durable Objects, and the latency and scale patterns for chat, multiplayer, and live dashboards.",
     "Serverless & Edge", "Advanced", ["edge", "websockets", "real-time", "durable objects", "latency"]),
    ("Portable Serverless: Write Once, Run Anywhere",
     "Vendor lock-in is the dirty secret of serverless. We cover the open frameworks — Knative, OpenFaaS, Spin — and the abstractions that let you move functions between clouds without rewriting.",
     "Serverless & Edge", "Beginner", ["serverless", "portability", "knative", "openfaas", "spin"]),

    # ========================= Developer Experience (Room 253) =========================
    ("The Inner Loop: Fast Feedback for Cloud Native Devs",
     "The gap between 'code saved' and 'see it running' defines developer happiness. We measure inner-loop latency and share the tooling and caching that bring it from minutes to seconds.",
     "Developer Experience", "Beginner", ["developer experience", "inner loop", "productivity", "dev tools", "feedback"]),
    ("Remote Development: Dev Containers and Cloud IDEs",
     "Your laptop is a bottleneck. We cover dev containers, GitHub Codespaces, and remote Kubernetes development, and the reproducible environments that make 'works on my machine' extinct.",
     "Developer Experience", "Intermediate", ["developer experience", "dev containers", "codespaces", "remote development", "tooling"]),
    ("Tilt, Skaffold, and the Art of Local K8s",
     "Developing against Kubernetes shouldn't mean waiting for image pushes. We compare Tilt and Skaffold, and show live-reload workflows that make local cluster development feel instant.",
     "Developer Experience", "Intermediate", ["developer experience", "tilt", "skaffold", "kubernetes", "local dev"]),
    ("Testing in Production: Feature Flags and Canaries",
     "Your staging environment lies to you. We make the case for testing in production with feature flags, canary releases, and the observability that makes it safe instead of terrifying.",
     "Developer Experience", "Intermediate", ["developer experience", "feature flags", "canary", "testing", "observability"]),
    ("The Developer Portal as a Superpower",
     "A good portal answers questions before they're asked. We show how a well-built developer portal cuts onboarding time and support load, and the content that actually gets used.",
     "Developer Experience", "Beginner", ["developer experience", "developer portal", "backstage", "onboarding", "documentation"]),
    ("Making Onboarding Not Suck",
     "Day-one productivity is a myth for most teams. We share the onboarding playbook — instant dev environments, golden-path tutorials, and a buddy system — that gets new hires shipping in days.",
     "Developer Experience", "Beginner", ["developer experience", "onboarding", "developer productivity", "culture", "documentation"]),
    ("CLI Design for Cloud Native Tools",
     "A CLI is a product with an API and a UX. We cover flag design, output formats, and the human factors that separate kubectl-caliber tools from the forgotten ones.",
     "Developer Experience", "Intermediate", ["developer experience", "cli", "ux", "design", "tooling"]),
    ("Contract Testing: Pact and API Compatibility",
     "Microservices break each other through silent API drift. We cover consumer-driven contract testing with Pact, and how it catches breaking changes before they reach production.",
     "Developer Experience", "Intermediate", ["developer experience", "contract testing", "pact", "api", "microservices"]),
    ("Progressive Delivery: Canary, Blue-Green, Argo Rollouts",
     "Ship every change safely with progressive delivery. We compare blue-green and canary strategies, and demo Argo Rollouts with automatic analysis and rollback.",
     "Developer Experience", "Intermediate", ["developer experience", "progressive delivery", "argo rollouts", "canary", "blue-green"]),
    ("Observability-Driven Development",
     "What if you wrote code with its telemetry already in mind? We show how thinking about traces and metrics during design produces debuggable systems and fewer 3am pages.",
     "Developer Experience", "Beginner", ["developer experience", "observability", "tracing", "design", "sre"]),
    ("AI Pair Programming at Scale",
     "Copilots are everywhere, but are teams actually faster? We share real adoption data, the workflow patterns that work, and the review practices that keep AI-generated code safe.",
     "Developer Experience", "Intermediate", ["developer experience", "ai", "copilot", "pair programming", "productivity"]),
    ("Monorepos vs Polyrepos: The Eternal Debate",
     "One repo or many? We present the real trade-offs in CI time, dependency management, and ownership, and the tooling — Bazel, Nx, Turborepo — that makes either choice work.",
     "Developer Experience", "Beginner", ["developer experience", "monorepo", "polyrepo", "bazel", "nx"]),
    ("From Bug Report to Fix: Shortening the Loop",
     "The distance between a user's bug and a deployed fix is a competitive advantage. We map the loop, find the bottlenecks, and share the tooling that compresses days into hours.",
     "Developer Experience", "Intermediate", ["developer experience", "feedback loops", "incident response", "deployment", "productivity"]),
    ("Local Kubernetes Clusters: kind, minikube, k3d",
     "You don't need a cloud to develop for Kubernetes. We compare kind, minikube, k3d, and Colima, and show how to configure them for fast iteration and realistic networking.",
     "Developer Experience", "Beginner", ["developer experience", "kind", "minikube", "k3d", "local dev"]),
    ("The Psychology of Developer Productivity",
     "Flow state, context switching, and meetings — productivity is human before it is technical. We cover the research and the practical changes that protect engineers' deep work.",
     "Developer Experience", "Beginner", ["developer experience", "productivity", "flow", "culture", "psychology"]),

    # ========================= Data & Streaming (The Loft) =========================
    ("Kafka at Scale: Lessons from a Trillion Messages",
     "Running Kafka at huge scale teaches hard lessons. We cover partition strategy, retention, and the consumer-group tuning that keeps a trillion-message pipeline from melting down.",
     "Data & Streaming", "Advanced", ["kafka", "streaming", "scale", "partitioning", "performance"]),
    ("Stream Processing with Flink on Kubernetes",
     "Flink on Kubernetes is powerful and finicky. We cover job submission, checkpointing to object storage, and autoscaling a Flink cluster that keeps state consistent under load.",
     "Data & Streaming", "Advanced", ["flink", "streaming", "kubernetes", "checkpointing", "state"]),
    ("Event Sourcing and CQRS in Cloud Native Systems",
     "Event sourcing gives you an audit log for free but complicates everything else. We cover the CQRS split, projections, and when event sourcing is worth it — and when it's not.",
     "Data & Streaming", "Advanced", ["event sourcing", "cqrs", "architecture", "streaming", "projections"]),
    ("Data Mesh: Governance Meets Autonomy",
     "Centralized data teams don't scale; data mesh decentralizes ownership. We explain the four principles, the platform that supports them, and the governance that keeps the mesh from becoming a mess.",
     "Data & Streaming", "Intermediate", ["data mesh", "governance", "data platform", "domain ownership", "architecture"]),
    ("Change Data Capture with Debezium",
     "Your database is a stream you're not reading. We cover Debezium, transaction logs, and the CDC pipelines that sync data to warehouses and caches without touching application code.",
     "Data & Streaming", "Intermediate", ["cdc", "debezium", "streaming", "databases", "etl"]),
    ("Real-Time Analytics with ClickHouse",
     "ClickHouse queries billions of rows in milliseconds. We cover the columnar design, the materialized views that keep dashboards fast, and when to reach for ClickHouse vs a warehouse.",
     "Data & Streaming", "Intermediate", ["clickhouse", "analytics", "olap", "columnar", "real-time"]),
    ("Kafka vs Redpanda vs Pulsar: A Benchmark",
     "The streaming space has options now. We benchmark Kafka, Redpanda, and Pulsar on throughput, latency, and operations, and give a decision guide for each.",
     "Data & Streaming", "Advanced", ["kafka", "redpanda", "pulsar", "benchmarks", "streaming"]),
    ("Schema Management and the Confluent Schema Registry",
     "Schemas are the contract of your data plane. We cover Avro/Protobuf/JSON Schema trade-offs, compatibility modes, and the registry patterns that prevent breaking consumers.",
     "Data & Streaming", "Intermediate", ["schema registry", "avro", "protobuf", "kafka", "compatibility"]),
    ("Data Lakehouse on Kubernetes: Iceberg and Friends",
     "The lakehouse merges warehouse performance with lake flexibility. We cover Apache Iceberg tables on object storage, Spark/Flink engines, and running it all on Kubernetes.",
     "Data & Streaming", "Advanced", ["data lakehouse", "iceberg", "spark", "kubernetes", "object storage"]),
    ("Streaming ETL: From Kafka to Warehouse",
     "Moving data from Kafka to a warehouse is easy until it's not. We cover exactly-once delivery, schema evolution, and the late-data handling that keeps your warehouse trustworthy.",
     "Data & Streaming", "Intermediate", ["etl", "kafka", "warehouse", "streaming", "exactly-once"]),
    ("Exactly-Once Semantics: A Practical Guide",
     "Exactly-once is a lie, but a useful one. We explain what the guarantees really mean across Kafka, Flink, and sinks, and the idempotency patterns that make them achievable.",
     "Data & Streaming", "Advanced", ["exactly-once", "kafka", "flink", "idempotency", "streaming"]),
    ("Time-Series Databases: InfluxDB, Timescale, Mimir",
     "Metrics, events, and sensor data need specialized storage. We compare time-series databases on ingestion, compression, and query patterns, and when Postgres (Timescale) is enough.",
     "Data & Streaming", "Intermediate", ["time-series", "influxdb", "timescale", "mimir", "metrics"]),
    ("Event-Driven Microservices: Patterns and Pitfalls",
     "Events decouple services but introduce eventual consistency. We cover the transactional outbox, retries with idempotent consumers, and the ordering pitfalls that bite distributed systems.",
     "Data & Streaming", "Intermediate", ["event-driven", "microservices", "outbox", "eventual consistency", "kafka"]),
    ("Data Quality in Streaming Pipelines",
     "Garbage in, garbage out, faster than ever. We cover schema validation, anomaly detection, and data contracts that catch bad data at the edge before it poisons downstream systems.",
     "Data & Streaming", "Intermediate", ["data quality", "streaming", "data contracts", "validation", "anomaly detection"]),
    ("Vector Search at Scale: Beyond RAG",
     "Vector search is everywhere now, but scale changes everything. We cover ANN indexes, hybrid BM25+vector retrieval, and the serving architecture behind low-latency semantic search.",
     "Data & Streaming", "Advanced", ["vector search", "embeddings", "ann", "hybrid search", "elasticsearch"]),
]

# ---------------------------------------------------------------------------
# Attendees
# ---------------------------------------------------------------------------
ATTENDEE_NAMES = [
    "Alex Johnson", "Morgan Lee", "Chris Patel", "Jamie Rivera", "Taylor Brooks",
    "Jordan Ellis", "Casey Nguyen", "Riley Thompson", "Avery Clark", "Quinn Martinez",
    "Skyler Adams", "Rowan Baker", "Hayden Foster", "Emerson Gray", "Parker Hall",
    "Sawyer Irwin", "Drew Jenkins", "Finley Kim", "Reese Lambert", "Cameron Moss",
    "Dakota Nunez", "Elliot Price", "Frankie Quinn", "Harper Reid", "Kendall Stone",
    "Logan Tate", "Micah Underwood", "Nico Vasquez", "Oakley Ward", "Perry Young",
    "Remi Zhao", "Sasha Ali", "Tatum Bell", "Val Carter", "Winter Diaz",
    "Blaire Evans", "Colby Frost", "Devon Gill", "Ezra Holt", "Fallon Irwin",
    "Greer Jackson", "Hollis King", "Ira Lane", "Jules Mason", "Keaton Nash",
    "Lennon Ortiz", "Marlow Park", "Noor Qadir", "Otis Reed", "Paxton Shaw",
    "Ren Tanaka", "Shay Ueda", "Teagan Vance", "Uma Wolf", "Vince Xu",
    "Wren Yates", "Zion Ahmed", "Ari Bloom", "Bo Chen", "Cleo Davies",
]

ATTENDEE_ROLES = [
    "Platform Engineer", "SRE", "DevOps Engineer", "Security Engineer",
    "ML Engineer", "Backend Engineer", "Data Engineer", "Staff Engineer",
    "Engineering Manager", "Solutions Architect", "Cloud Architect", "Developer Advocate",
    "Site Reliability Engineer", "Infrastructure Engineer", "Software Engineer",
    "Principal Engineer", "Data Scientist", "Product Manager", "CTO", "Student",
]

ATTENDEE_COMPANIES = [
    "SaltStack Labs", "Wasatch Cloud", "RedRock Software", "Bonneville Systems",
    "Zion Data", "Canyon Dev Co", "Timpanogos Tech", "Uinta Analytics",
    "Deseret Digital", "Snowbird Software", "Alta Cloud", "Sundance Systems",
    "Park City Platform", "Moab Mesh", "Ogden Ops", "Provo Pipeline",
    "Layton Labs", "Draper Dev", "Lehi Logic", "Murray Microservices",
]

# Topic vocabulary for interests — overlaps heavily with talk tags so that
# attendee/talk matchmaking and interest-based search both work.
INTEREST_TOPICS = [
    "kubernetes", "ebpf", "security", "observability", "opentelemetry", "prometheus",
    "service mesh", "istio", "cilium", "networking", "serverless", "webassembly",
    "edge", "ai", "llm", "rag", "vector databases", "platform engineering",
    "gitops", "argo cd", "devops", "sre", "developer experience", "backstage",
    "ci/cd", "terraform", "mlops", "gpu", "fine-tuning", "zero trust",
    "supply chain", "falco", "policy as code", "secrets management", "cost optimization",
    "multi-cluster", "distributed tracing", "chaos engineering", "kafka", "streaming",
    "data mesh", "clickhouse", "flink", "event-driven", "containers", "docker",
]


def make_talks():
    talks = []
    idx = 1
    for track, room in TRACK_ROOMS.items():
        track_talks = [t for t in TALKS if t[2] == track]
        assert len(track_talks) == 15, f"{track} has {len(track_talks)} talks"
        for slot_index, (title, abstract, _, level, tags) in enumerate(track_talks):
            if slot_index < 8:
                day, time = DAY1, SLOT_TIMES_DAY1[slot_index]
            else:
                day, time = DAY2, SLOT_TIMES_DAY2[slot_index - 8]

            # Deterministic speaker assignment: 1-3 speakers per talk.
            rng = random.Random(idx * 7919)
            n_speakers = rng.choice([1, 2, 2, 2, 3])
            speakers = rng.sample(SPEAKERS, n_speakers)

            talks.append({
                "id": f"talk-{idx:03d}",
                "title": title,
                "abstract": abstract,
                "speakers": speakers,
                "track": track,
                "room": room,
                "start_time": f"{day}T{time}:00-07:00",
                "level": level,
                "tags": tags,
            })
            idx += 1
    return talks


def make_attendees():
    attendees = []
    rng = random.Random(20261109)
    names = list(ATTENDEE_NAMES)
    rng.shuffle(names)
    for i, name in enumerate(names, start=1):
        n_interests = rng.randint(3, 6)
        interests = sorted(rng.sample(INTEREST_TOPICS, n_interests))
        attendees.append({
            "id": f"attendee-{i:03d}",
            "name": name,
            "role": rng.choice(ATTENDEE_ROLES),
            "company": rng.choice(ATTENDEE_COMPANIES),
            "interests": interests,
        })
    return attendees


def main():
    root = Path(__file__).parent
    talks = make_talks()
    attendees = make_attendees()

    (root / "talks.json").write_text(json.dumps(talks, indent=2) + "\n")
    (root / "attendees.json").write_text(json.dumps(attendees, indent=2) + "\n")

    # Sanity checks
    tracks = {}
    for t in talks:
        tracks[t["track"]] = tracks.get(t["track"], 0) + 1
        assert t["start_time"].endswith("-07:00"), t["id"]
    print(f"Wrote {len(talks)} talks across {len(tracks)} tracks.")
    for k, v in sorted(tracks.items()):
        print(f"  {k}: {v}")
    print(f"Wrote {len(attendees)} attendees.")


if __name__ == "__main__":
    main()
