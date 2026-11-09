#!/usr/bin/env python3
"""Build and validate the ConfPilot seed glossary (200 terms).

Writes glossary.json (for the app + Elasticsearch `terms` index) and glossary.csv
(for humans). Fails loudly if any rule is broken, so it can run in CI.

Usage:
  python3 build_glossary.py                      # validate, write glossary.json/.csv, check the talk track
  python3 build_glossary.py --check t1.txt ...   # score STT transcripts: the 5 target terms must all be caught

Row format:  id | term | aliases(;) | category | level | say | simple_def | prereqs(;)
Levels: 1 business + idioms · 2 general tech · 3 cloud-native / AI practitioner · 4 specialist
"""
import csv, json, re, sys
from pathlib import Path

ROWS = r"""
ipo|IPO|initial public offering;pre-IPO;going public;goes public|business|1|eye-pee-oh|When a private company first sells its shares to the public on the stock market.|equity
series-funding|Series A / B / C|Series A;Series B;Series C;funding round;seed round|business|1||A stage when investors give a startup money in exchange for owning part of it.|venture-capital
venture-capital|venture capital|VC;VCs;venture capitalist|business|1|vee-see|Investors who give money to young, risky companies hoping they grow very large.|equity
equity|equity|stock options|business|1||Owning a part of a company, usually as shares.|
valuation|valuation|valued at|business|1||How much money people agree a company is worth.|
runway|runway||business|1||How many months a company can keep operating before its money runs out.|burn-rate
burn-rate|burn rate||business|1||How much money a company spends each month beyond what it earns.|
arr|ARR|annual recurring revenue|business|2|ay-ar-ar|Money a company expects to earn every year from subscriptions.|saas
saas|SaaS|software as a service|business|2|sass|Software you rent online by subscription instead of installing and owning it.|cloud
b2b|B2B|business to business|business|1|bee-two-bee|A company that sells to other companies, not to regular people.|
go-to-market|go-to-market|GTM;go to market|business|1||The plan for how a product will reach and be sold to customers.|
product-market-fit|product-market fit|PMF;product market fit|business|2||When many customers clearly want and pay for what you built.|
roi|ROI|return on investment|business|1|ar-oh-eye|How much value you get back compared with what you spent.|
kpi|KPI|KPIs;key performance indicator|business|1|kay-pee-eye|A number a team watches to see if it is reaching its goals.|
okr|OKR|OKRs;objectives and key results|business|1|oh-kay-ar|A goal plus a few measurable results that show if the goal was met.|kpi
stakeholder|stakeholder|stakeholders|business|1||A person or group affected by a project who cares how it turns out.|
roadmap|roadmap|road map|business|1||A plan showing what a team will build and roughly when.|
mvp|MVP|minimum viable product|business|1|em-vee-pee|The simplest version of a product that real users can try.|
pivot|pivot|pivoted|business|1||When a company changes direction to a new product or market.|
churn|churn|churn rate|business|2||The share of customers who stop paying over a period.|
unicorn|unicorn|unicorns|business|1||A private startup valued at more than one billion dollars.|valuation
acquisition|acquisition|M&A;acquired;acquires|business|1||When one company buys another company.|
moat|moat||business|2||Something that makes it hard for competitors to copy a company.|
vendor-lock-in|vendor lock-in|lock-in;locked in|business|2||When switching away from a supplier is so hard or costly that you stay.|
poc|POC|proof of concept;PoC|business|1|pee-oh-see|A small test to show an idea can work before building it fully.|
enterprise|enterprise|enterprise customers|business|1||Large companies, which usually need extra security, support, and contracts.|
sla|SLA|SLAs;service level agreement|business|2|ess-el-ay|A written promise to customers about uptime or speed, often with penalties.|uptime
keynote|keynote|keynotes|conference|1||The main talk of a conference, usually given to everyone at once.|
breakout-session|breakout session|breakout;breakouts|conference|1||A smaller talk that runs at the same time as other talks.|
hallway-track|hallway track||conference|1||The useful conversations people have between talks, outside the rooms.|
lightning-talk|lightning talk|lightning talks|conference|1||A very short talk, usually five minutes or less.|
cfp|CFP|call for papers;call for proposals|conference|2|see-eff-pee|The open request for people to submit talk ideas to a conference.|
booth|booth|expo hall;sponsor booth|conference|1||A company's stand at a conference where you can meet its team.|
swag|swag||conference|1||Free items companies give away, like stickers and t-shirts.|
circle-back|circle back|circling back;circle back on|idiom|1||To return to a topic later.|
take-offline|take it offline|take this offline|idiom|1||To discuss something later, privately, not in the current meeting.|
ping|ping me|pinged|idiom|1||Send someone a short message.|
bandwidth|bandwidth|no bandwidth|idiom|1||Free time or energy to take on more work. In networks: how much data can move.|
low-hanging-fruit|low-hanging fruit|low hanging fruit|idiom|1||Easy tasks that give good results quickly.|
move-the-needle|move the needle|moves the needle|idiom|1||To make a change big enough to notice.|
boil-the-ocean|boil the ocean|boiling the ocean|idiom|1||To try to do far too much at once.|
table-stakes|table stakes||idiom|1||The basic features everyone expects; you need them just to compete.|
dogfooding|dogfooding|dogfood;eat our own dog food|idiom|1||When a company uses its own product every day.|
north-star-metric|north star metric|north star|idiom|2||The one number a team uses to judge if it is succeeding.|kpi
deep-dive|deep dive||idiom|1||A long, detailed look at one topic.|
api|API|APIs;application programming interface|tech|2|ay-pee-eye|A set of rules that lets one program ask another program for data or actions.|
sdk|SDK|software development kit|tech|2|ess-dee-kay|A package of tools and code that makes building on a platform easier.|api
cloud|cloud|the cloud;cloud computing|tech|2||Renting computers and storage over the internet instead of owning them.|server
server|server|servers|tech|2||A computer that runs programs and answers requests from other computers.|
database|database|DB;databases|tech|2||Organized storage for data that programs can search and update.|
latency|latency|low latency;high latency|tech|2|LAY-ten-see|The delay between asking for something and getting the answer.|
throughput|throughput||tech|2|THROO-put|How much work a system finishes in a period of time.|
frontend|frontend|front end;front-end|tech|2||The part of software that users see and touch.|
backend|backend|back end;back-end|tech|2||The part of software that runs on servers, out of the user's sight.|server
open-source|open source|open-source;OSS|tech|2||Software whose code is public, so anyone can read, use, and change it.|
repository|repository|repo;repos|tech|2|ri-POZ-i-tor-ee|The place where a project's code and its history are stored.|git
git|Git||tech|2|git (hard g)|A tool that tracks every change to code and who made it.|
pull-request|pull request|PR;PRs;merge request;pull requests|tech|2||A proposed code change that teammates review before it is accepted.|git
commit|commit|commits|tech|2||A saved snapshot of code changes, with a short message.|git
branch|branch|branches|tech|2||A separate copy of the code where you can work without affecting others.|git
merge|merge|merged;merging|tech|2||Combining changes from one branch into another.|branch
code-review|code review|code reviews|tech|2||When teammates read your code changes to find problems before they ship.|pull-request
ci-cd|CI/CD|CI;CD;continuous integration;continuous delivery;continuous deployment|tech|2|see-eye see-dee|Automatic testing and shipping of code every time someone changes it.|commit
deploy|deploy|deployed;deploying|tech|2||To put a new version of software where users can use it.|
production|production|prod;in production|tech|2||The live system that real users are using.|
staging|staging|staging environment|tech|2||A copy of the live system for testing before release.|production
bug|bug|bugs|tech|2||A mistake in software that makes it behave wrongly.|
hotfix|hotfix|hot fix|tech|2||An urgent fix shipped quickly to repair a live problem.|bug;production
rollback|rollback|roll back;rolled back|tech|2||Returning to the previous working version after a bad release.|deploy
refactor|refactor|refactoring|tech|2|ree-FAK-ter|Rewriting code to make it cleaner without changing what it does.|
technical-debt|technical debt|tech debt|tech|2||Shortcuts in code that save time now but cost more work later.|
legacy|legacy|legacy code;legacy system|tech|2||Old software that still runs but is hard to change.|
monolith|monolith|monolithic|tech|2|MON-oh-lith|One big application where all parts are built and deployed together.|
microservices|microservices|microservice|tech|3||Building an app as many small services that talk to each other.|api;monolith
scalability|scalability|scalable;scale out;scaling|tech|2||Being able to handle more users or data without breaking.|
load-balancer|load balancer|load balancing;load balancers|tech|3||A system that spreads incoming traffic across several servers.|server
cache|cache|caching;cached|tech|2|cash|A fast copy of data kept close by so it loads quicker.|
cdn|CDN|content delivery network|tech|3|see-dee-en|Servers around the world that deliver files from a location near each user.|cache
dns|DNS|domain name system|tech|3|dee-en-ess|The internet's address book that turns website names into server addresses.|
webhook|webhook|webhooks|tech|3||A message one app sends to another automatically when something happens.|api
authentication|authentication|auth;authn|tech|2||Checking who you are, for example with a password.|
authorization|authorization|authz;permissions|tech|2||Checking what you are allowed to do after you log in.|authentication
encryption|encryption|encrypted;encrypt|tech|2||Scrambling data so only people with the right key can read it.|
uptime|uptime||tech|2||The share of time a system is working and available.|
outage|outage|downtime;outages|tech|2||A period when a service is not working for users.|
serverless|serverless|functions as a service;FaaS;Lambda|tech|3||Running code without managing servers; the provider runs it only when needed.|cloud;server
agile|agile||tech|1||A way of working in short cycles, delivering small pieces often.|
sprint|sprint|sprints|tech|1||A short fixed period, often two weeks, to finish a set of work.|agile
standup|standup|stand-up;daily standup|tech|1||A short daily team meeting to share progress and problems.|
edge-case|edge case|edge cases;corner case|tech|2||An unusual situation that software may not handle well.|
regression|regression|regressed|tech|2||When something that used to work breaks after a change.|bug
linux|Linux||tech|2|LIN-ux|A free, open-source operating system that runs most servers.|open-source
yaml|YAML|yml|tech|3|YAM-ul|A simple text format for writing settings, used a lot in Kubernetes.|
json|JSON||tech|2|JAY-son|A common text format for sending structured data between programs.|
data-pipeline|data pipeline|pipeline;ETL|tech|3||Automatic steps that move and clean data from one place to another.|database
real-time|real-time|realtime;real time|tech|2||Happening right away, with almost no delay.|latency
event-driven|event-driven|event driven|tech|3||A design where parts of a system react when something happens.|
container|container|containers|cloud|3||A package holding an app and everything it needs, so it runs the same anywhere.|
docker|Docker||cloud|3||The most popular tool for building and running containers.|container
container-image|container image|image;docker image;images|cloud|3||The saved template a container starts from.|container
container-registry|container registry|registry;image registry|cloud|3||A storage place for container images.|container-image
kubernetes|Kubernetes|K8s;kube|cloud|3|koo-ber-NET-eez|Open-source software that runs and manages many containers across many computers.|container
cluster|cluster|clusters|cloud|3||A group of computers working together as one system.|server
node|node|nodes;worker node|cloud|3||One computer, real or virtual, inside a cluster.|cluster
pod|pod|pods|cloud|3||The smallest unit Kubernetes runs: one or a few containers together.|kubernetes;container
k8s-deployment|Deployment (Kubernetes)|Deployment|cloud|3||Kubernetes settings that keep a chosen number of copies of an app running.|pod
k8s-service|Service (Kubernetes)|Service|cloud|3||A stable address in Kubernetes that sends traffic to the right pods.|pod
ingress|ingress|ingress controller|cloud|4|IN-gress|Kubernetes rules for how outside web traffic reaches services inside the cluster.|k8s-service
namespace|namespace|namespaces|cloud|3||A named area inside a cluster that keeps teams' resources separate.|cluster
helm|Helm|Helm chart;Helm charts|cloud|3||A package manager for Kubernetes that installs apps with one command.|kubernetes
kubectl|kubectl|kube control;cube control;cube cuddle|cloud|3|KOOB-control (some say "cube cuddle")|The command-line tool for talking to a Kubernetes cluster.|kubernetes
control-plane|control plane||cloud|4||The brain of a Kubernetes cluster that decides where things run.|cluster
etcd|etcd||cloud|4|ET-see-dee|The database where Kubernetes stores the state of the cluster.|control-plane
k8s-operator|operator (Kubernetes)|operator;operators|cloud|4||Software that automatically runs and repairs a complex app inside Kubernetes.|kubernetes
crd|CRD|CRDs;custom resource;custom resource definition|cloud|4|see-ar-dee|A way to add your own object types to Kubernetes.|kubernetes
manifest|manifest|manifests|cloud|3||A file, usually YAML, that describes what should run in Kubernetes.|yaml
autoscaling|autoscaling|HPA;horizontal pod autoscaler;autoscaler|cloud|3||Automatically adding or removing copies of an app as traffic changes.|scalability
replica|replica|replicas|cloud|3|REP-li-ka|One identical copy of an app or database.|
crashloopbackoff|CrashLoopBackOff|crash loop;crashlooping;crash loop back off|cloud|4|crash-loop-back-off|A pod that keeps crashing and restarting, with longer waits between tries.|pod
oomkilled|OOMKilled|OOM;out of memory;OOM killed|cloud|4|oom-killed|A container was stopped because it used more memory than allowed.|container
sidecar|sidecar|sidecars|cloud|4||A helper container that runs next to the main app in the same pod.|pod
service-mesh|service mesh|Istio;Linkerd|cloud|4||A layer that controls, secures, and observes traffic between microservices.|microservices
ebpf|eBPF||cloud|4|ee-bee-pee-eff|A way to run small safe programs inside the Linux kernel to watch or control the system.|linux
gitops|GitOps|Argo CD;ArgoCD|cloud|3|GIT-ops|Managing systems by changing files in Git, which tools then apply automatically.|git;deploy
infrastructure-as-code|infrastructure as code|IaC;Terraform|cloud|3||Creating servers and networks from code files instead of clicking in a console.|cloud
multi-cloud|multi-cloud|multicloud;multi cloud|cloud|3||Using more than one cloud provider at the same time.|cloud
platform-engineering|platform engineering|platform team;internal developer platform;IDP|cloud|3||A team building shared tools so other developers can ship easily on their own.|devops
devops|DevOps||cloud|2|dev-ops|Developers and operations working together to ship and run software faster.|
sre|SRE|site reliability engineering;site reliability engineer;SREs|ops|3|ess-ar-ee|Engineers who use software to keep live systems reliable and fast.|production
cncf|CNCF|Cloud Native Computing Foundation|cloud|2|see-en-see-eff|The nonprofit that hosts Kubernetes and many other open-source projects; it runs KubeCon.|open-source
cloud-native|cloud native|cloud-native|cloud|3||Software designed from the start to run on cloud platforms in containers.|cloud;container
workload|workload|workloads|cloud|3||Any app or job running on a system.|
orchestration|orchestration|orchestrator|cloud|3||Automatically starting, stopping, and placing many containers across machines.|container
zero-trust|zero trust|zero-trust|cloud|3||Security that checks every request, never trusting anything just because it is inside.|authentication
rbac|RBAC|role-based access control|cloud|3|AR-back|Giving permissions to roles, then giving roles to people.|authorization
secrets-management|secrets management|secrets manager|cloud|3||Safely storing passwords and keys that programs need.|encryption
supply-chain-security|supply chain security|software supply chain|cloud|4||Protecting all the code and tools your software is built from.|open-source
sbom|SBOM|software bill of materials|cloud|4|ESS-bom|A list of every component inside a piece of software.|supply-chain-security
cve|CVE|CVEs;vulnerability;vulnerabilities|cloud|3|see-vee-ee|A publicly listed security weakness with an ID number.|
gpu|GPU|GPUs;graphics processing unit|ai|2|jee-pee-yoo|A chip that does many calculations at once; it powers AI.|
observability|observability|o11y|ops|3|ob-ZER-va-BIL-i-tee|Being able to understand what a live system is doing from the data it sends out.|telemetry
monitoring|monitoring||ops|2||Watching a system's health and warning people when something looks wrong.|
telemetry|telemetry||ops|3|te-LEM-e-tree|Data a system sends about itself: logs, metrics, and traces.|
opentelemetry|OpenTelemetry|OTel;open telemetry|ops|3|OH-tel|An open standard for collecting telemetry from any app.|telemetry
trace|trace|traces;tracing;distributed tracing|ops|3||A record of one request's full path through many services, with timing.|microservices
span|span|spans|ops|4||One timed step inside a trace.|trace
logs|logs|logging|ops|2||Time-stamped text messages a program writes about what it did.|
metrics|metrics|metric|ops|2||Numbers measured over time, like requests per second.|
dashboard|dashboard|dashboards|ops|2||A screen of charts showing a system's health at a glance.|metrics
alert|alert|alerts;alerting|ops|2||An automatic warning sent when something crosses a limit.|monitoring
sli|SLI|SLIs;service level indicator|ops|3|ess-el-eye|A measurement of how well a service works for users, like success rate.|metrics
slo|SLO|SLOs;service level objective|ops|3|ess-el-oh|A target for a reliability measurement, like 99.9% of requests succeed.|sli
error-budget|error budget|budget burn|ops|4||How much failure an SLO allows before the team must stop and fix reliability.|slo
percentile-latency|p99|p95;p50;tail latency|ops|3|pee-ninety-nine|The time within which 99% of requests finish; the slowest 1% take longer.|latency
mttr|MTTR|mean time to recovery;mean time to resolve|ops|3|em-tee-tee-ar|The average time it takes to fix a problem.|incident
incident|incident|incidents|ops|2||An unplanned problem that hurts a service and needs a fast response.|
on-call|on-call|on call|ops|2||Being the person who must respond if the system breaks, even at night.|incident
paging|paging|paged;pager|ops|2||Urgently alerting the on-call engineer by phone.|on-call
postmortem|postmortem|post-mortem;incident review|ops|2||A written review after an incident about what happened and how to prevent it.|incident
root-cause|root cause|RCA;root cause analysis|ops|2||The deepest reason a problem happened, not just its symptoms.|
rum|RUM|real user monitoring|ops|3|rum|Measuring the speed and errors real users see in their browsers or apps.|monitoring
apm|APM|application performance monitoring|ops|3|ay-pee-em|Tools that measure how fast an app responds and where it slows down.|monitoring
chaos-engineering|chaos engineering|chaos testing|ops|4||Breaking things on purpose to check that a system recovers.|
toil|toil||ops|3||Repetitive manual work that could be automated.|
runbook|runbook|runbooks|ops|3||Step-by-step instructions for handling a known problem.|incident
ai-sre|AI SRE|AI SRE agent|ops|4||An AI agent that investigates incidents and suggests fixes for engineers.|sre;ai-agent
machine-learning|machine learning|ML|ai|2||Computers learning patterns from data instead of following hand-written rules.|
llm|LLM|LLMs;large language model;large language models|ai|3|el-el-em|An AI model trained on huge amounts of text that can read and write language.|machine-learning
prompt|prompt|prompts;prompt engineering|ai|2||The instructions or question you give to an AI model.|
token|token|tokens|ai|3||A small piece of text, often part of a word, that an AI model reads.|llm
context-window|context window||ai|3||How much text an AI model can read at once.|token
hallucination|hallucination|hallucinate;hallucinating;hallucinations|ai|3||When an AI confidently says something that is false.|llm
fine-tuning|fine-tuning|fine-tune;fine tuning;fine tuned|ai|4||Extra training of a model on your own examples to make it better at one task.|llm
inference|inference|inference serving|ai|3|IN-fer-ence|Using a trained model to get answers, as opposed to training it.|machine-learning
embedding|embedding|embed;embeds;embeddings;vector embeddings;vector embedding|ai|3||Turning text into a list of numbers that captures its meaning, so similar meanings sit close together.|vector;machine-learning
vector|vector|vectors|ai|3||A list of numbers that stands for something, like the meaning of a sentence.|
vector-database|vector database|vector DB;vector store|data|3||A database that finds items with similar meaning by comparing embeddings.|embedding;database
rag|RAG|retrieval-augmented generation;retrieval augmented generation|ai|3|rag|Giving an AI relevant documents from a search first, so its answer uses real facts.|llm;semantic-search
chunking|chunking|chunks;chunk|ai|3||Splitting long documents into small pieces so search and AI can use them.|rag
ai-agent|AI agent|agent;agents;agentic;AI agents|ai|3||An AI that can plan steps and use tools to finish a task by itself.|llm
mcp|MCP|Model Context Protocol|ai|4|em-see-pee|An open standard that lets AI agents connect to tools and data.|ai-agent
guardrails|guardrails||ai|3||Rules and checks that stop an AI from doing harmful or wrong things.|llm
evals|evals|eval;evaluations|ai|3||Tests that measure how well an AI system does its job.|llm
gen-ai|generative AI|GenAI;gen AI|ai|2||AI that creates new text, images, code, or sound.|
speech-to-text|speech-to-text|STT;ASR;speech to text|ai|3||Turning spoken words into written text automatically.|
keyword-search|keyword search|lexical search;full-text search|data|3||Finding documents that contain the exact words you typed.|
semantic-search|semantic search||data|3|se-MAN-tik|Finding results by meaning, even if they use different words.|embedding
hybrid-search|hybrid search||data|3||Combining keyword search and semantic search to get better results.|keyword-search;semantic-search
bm25|BM25||data|4|bee-em-twenty-five|A classic formula for ranking keyword search results.|keyword-search
rrf|RRF|reciprocal rank fusion|data|4|ar-ar-eff|A way to merge two ranked result lists into one.|hybrid-search
reranker|reranker|reranking;rerank;rerankers|data|4||A model that reorders search results so the most relevant come first.|semantic-search
search-index|index|indices;indexes;indexing|data|3||A structure that makes searching data fast, like the list at the back of a book.|database
percolator|percolator|percolate;percolate query|data|4||A search that runs backwards: stored queries are checked against each new document.|search-index
retrieval|retrieval|retrieve;retrieved;retriever|data|3||Finding and fetching the most useful pieces of information for a question.|search-index
knowledge-base|knowledge base|knowledge bases|ai|2||A collection of documents that people or an AI can search to find answers.|
query|query|queries|data|2|KWEER-ee|A question or search request sent to a database or search engine.|
relevance|relevance|relevant;relevancy|data|2||How well a search result matches what the person was looking for.|query
use-case|use case|use cases|business|1||A specific situation or problem that a product is used to solve.|
managed-service|managed service|managed;managed services;fully managed|business|2||A product the provider runs and maintains for you, so your team does not operate it.|cloud
elasticsearch|Elasticsearch|Elastic;Elastic Search|data|3|ee-LAS-tik-search|A popular search engine and database for keyword, semantic, and hybrid search.|search-index
"""

# Common English words: the matcher should require tech context (or case match) before popping a card.
AMBIGUOUS = {
    "k8s-deployment", "k8s-service", "k8s-operator", "search-index", "node", "container-image",
    "token", "branch", "commit", "merge", "span", "logs", "alert", "pivot", "runway", "equity",
    "manifest", "sprint", "legacy", "regression", "prompt", "enterprise", "ping", "bandwidth",
    "ai-agent", "trace", "retrieval", "relevance", "managed-service",
}

LEVELS = {1: "business, conference and idioms", 2: "general tech", 3: "cloud-native and AI practitioner", 4: "specialist"}

DEMO_SCRIPT = """
Clayton: I work at Radar, we do SRE for Kubernetes clusters. What do you do?
Zack: I work at Elasticsearch, we do managed hybrid search, including RAG and keyword search.
Clayton: Nice! So that will help power apps' search engines, or what are customers trying to do with your technology?
Zack: Yeah, for sure! Wikipedia is one of our customers. Nowadays, a lot of our customers are using our product to embed
thousands of documents into a knowledge base the agent can pull from.
Clayton: Interesting, so those documents are turned into vectors that can be retrieved easily. How does your search
service determine what is most relevant to the agent or user's query?
Zack: Great question! It uses BM25 for keyword matches, while the embeddings handle meaning, and RRF to rank the results
to return to the user or agent.
Clayton: Oh, makes sense! At Radar, we have some internal search service use cases, can I get your LinkedIn?
"""

# The demo must catch these every time (bolded in the team doc).
TARGETS = ["sre", "rag", "embedding", "bm25", "rrf"]

NUM_WORDS = {"twenty five": "25", "twenty-five": "25"}


def normalize(text):
    """Undo common STT formatting so the matcher sees canonical forms.
    'R.R.F.' / 'R R F' -> 'RRF', 'BM 25' / 'B.M. 25' / 'BM twenty five' -> 'BM25'."""
    for words, digits in NUM_WORDS.items():
        text = re.sub(rf"\b{words}\b", digits, text, flags=re.I)
    text = re.sub(r"\b((?:[A-Za-z]\.){2,})", lambda m: m.group(1).replace(".", ""), text)       # R.R.F. -> RRF
    text = re.sub(r"\b([A-Za-z])(?: ([A-Za-z])\b){1,3}", lambda m: m.group(0).replace(" ", "")
                  if all(len(w) == 1 for w in m.group(0).split()) else m.group(0), text)      # R R F -> RRF
    text = re.sub(r"\bBM[\s-]?25\b", "BM25", text, flags=re.I)
    text = re.sub(r"\bElasticS[a-z]{2,6}\b", "Elasticsearch", text)  # Whisper: ElasticSarc/ElasticSuck/ElasticSock
    return text



def surface_forms(t):
    base = re.sub(r"\s*\(.*?\)\s*", "", t["term"]).strip()
    forms = {base, *t["aliases"]}
    if "/" in base:  # "Series A / B / C" is a label, not a spoken form
        forms.discard(base)
    return {f for f in forms if f}


def build():
    terms, errors = [], []
    for n, line in enumerate(l for l in ROWS.strip().splitlines() if l.strip()):
        parts = line.split("|")
        if len(parts) != 8:
            errors.append(f"row {n + 1}: expected 8 fields, got {len(parts)}: {line[:60]}")
            continue
        tid, term, aliases, cat, level, say, definition, prereqs = (p.strip() for p in parts)
        terms.append({
            "id": tid,
            "term": term,
            "aliases": [a.strip() for a in aliases.split(";") if a.strip()],
            "category": cat,
            "level": int(level),
            "say": say or None,
            "simple_def": definition,
            "prereqs": [p.strip() for p in prereqs.split(";") if p.strip()],
            "ambiguous": tid in AMBIGUOUS,
            "source": "seed",
            "translations": {},  # filled by the LLM batch job (es, zh, hi, pt)
        })

    ids = [t["id"] for t in terms]
    byid = {t["id"]: t for t in terms}
    if len(terms) != 200:
        errors.append(f"expected 200 terms, got {len(terms)}")
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"duplicate ids: {sorted(dupes)}")
    for i in AMBIGUOUS - set(ids):
        errors.append(f"AMBIGUOUS names unknown id {i}")

    owner = {}
    for t in terms:
        words = len(t["simple_def"].split())
        if words > 20:
            errors.append(f"{t['id']}: definition has {words} words (max 20)")
        if t["level"] not in LEVELS:
            errors.append(f"{t['id']}: level {t['level']} not in 1-4")
        for p in t["prereqs"]:
            if p not in byid:
                errors.append(f"{t['id']}: prereq '{p}' does not exist")
        for form in surface_forms(t):
            if re.search(rf"(?<!\w){re.escape(form)}(?!\w)", t["simple_def"], re.I):
                errors.append(f"{t['id']}: definition uses its own term '{form}'")
            key = form.lower()
            if key in owner and owner[key] != t["id"]:
                errors.append(f"alias '{form}' maps to both {owner[key]} and {t['id']}")
            owner[key] = t["id"]

    # prerequisite graph must be acyclic
    state = {}
    def visit(i, path):
        if state.get(i) == 1:
            errors.append(f"prereq cycle: {' -> '.join(path + [i])}")
            return
        if state.get(i) == 2:
            return
        state[i] = 1
        for p in byid[i]["prereqs"]:
            if p in byid:
                visit(p, path + [i])
        state[i] = 2
    for i in ids:
        visit(i, [])
    return terms, errors


def match(text, terms):
    """Tier-1 matcher sketch: longest surface form first, word boundaries, case-insensitive."""
    forms = sorted(((f, t["id"]) for t in terms for f in surface_forms(t)), key=lambda x: -len(x[0]))
    found, taken = [], [False] * len(text)
    for form, tid in forms:
        for m in re.finditer(rf"(?<!\w){re.escape(form)}(?!\w)", text, re.I):
            if not any(taken[m.start():m.end()]):
                taken[m.start():m.end()] = [True] * (m.end() - m.start())
                found.append((m.start(), tid, m.group(0)))
    return [(tid, s) for _, tid, s in sorted(found)]


def check_transcripts(paths, terms):
    """Score STT transcripts against the reference talk track. Exit 1 if any TARGET is missed."""
    expected = {tid for tid, _ in match(DEMO_SCRIPT, terms)}
    failed = False
    for path in paths:
        got = {tid for tid, _ in match(normalize(Path(path).read_text()), terms)}
        missed_targets = [t for t in TARGETS if t not in got]
        recall = len(expected & got) / len(expected)
        failed |= bool(missed_targets)
        print(f"{Path(path).name}: targets {len(TARGETS) - len(missed_targets)}/{len(TARGETS)}"
              f"{' MISSED ' + ', '.join(missed_targets) if missed_targets else ''} | "
              f"talk-track terms {len(expected & got)}/{len(expected)} ({recall:.0%})"
              f"{' | missing: ' + ', '.join(sorted(expected - got)) if expected - got else ''}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    terms, errors = build()
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        check_transcripts(sys.argv[2:], terms)
    if errors:
        print("GLOSSARY INVALID:\n  " + "\n  ".join(errors))
        sys.exit(1)
    (out / "glossary.json").write_text(json.dumps(
        {"version": 1, "generated": "2026-11-09", "levels": LEVELS, "terms": terms}, indent=2, ensure_ascii=False) + "\n")
    with open(out / "glossary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "term", "aliases", "category", "level", "say", "simple_def", "prereqs", "ambiguous"])
        for t in terms:
            w.writerow([t["id"], t["term"], "; ".join(t["aliases"]), t["category"], t["level"], t["say"] or "",
                        t["simple_def"], "; ".join(t["prereqs"]), t["ambiguous"]])
    counts = {}
    for t in terms:
        counts[t["category"]] = counts.get(t["category"], 0) + 1
    print(f"OK: {len(terms)} terms ->", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    hits = match(DEMO_SCRIPT, terms)
    missing = [t for t in TARGETS if t not in {h[0] for h in hits}]
    if missing:
        print(f"TALK TRACK MISSES TARGETS: {missing}")
        sys.exit(1)
    print(f"Demo script triggers {len(hits)} cards ({len({h[0] for h in hits})} distinct terms):")
    print("  " + ", ".join(f"{s}" for _, s in hits))
