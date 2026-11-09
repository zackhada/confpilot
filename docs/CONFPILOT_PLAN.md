# ConfPilot: Build, Demo & Pitch Plan

Nov 9, 2026 · Skyler Smith · Snapshot of the team planning doc at 12:15 PM. From here on, change it by PR.

ConfPilot decodes the jargon each attendee does not know, the moment it is said, then turns the conference into their personal study plan. This plan gets a working phone demo by 3:45 PM and submits at 5:15 PM.

## Fix first

The team is staying on AWS and keeping the current repo. That works, but three things need handling today.

1. **Move pre-kickoff code out of the repo in the first PR.** The scaffold in `zackhada/confpilot` was committed between 9:09 and 9:35 AM, before the 11:00 start. The rules say main coding must begin after kickoff and disqualify previously built projects; Zack's `docs/HACKATHON.md` says the same. Since we're keeping the repo:
   - Move the old `app/`, `data/` and `deploy/` code into a `reference/` folder, or delete it, through a Gitar-reviewed PR.
   - Write all ConfPilot code after 11:00, through PRs.
   - Say this plainly in the README. Judges can see the commit history.
2. **Don't use the staged OOM incident.** The repo's `deploy/overlays/oom-fix` is a pre-planned fix for an embed-worker running out of memory. Radar's guidance says "don't break things on purpose for the demo." Investigate only real issues. If nothing breaks, investigate after a release; an all-clear with evidence counts.
3. **Get public HTTPS on EKS early.** Phones only allow mic access over HTTPS. Clayton needs:
   - an ALB (AWS Load Balancer Controller) with an ACM certificate
   - a DNS name, such as `confpilot.skylersmith.me` on Skyler's Namecheap account
   - images built in CI for the node architecture and pushed to ECR
   - the cluster connected to Radar Cloud, or `kubectl radar` running locally

   If EKS stalls, Radar's starter template is the fallback. It comes with a ready team cluster at `https://<team>.cnh.radarhq.io`.

Other rules and facts:

- **The schedule may differ.** The official one, from the repo's HACKATHON.md, has build 11:00–2:00, lunch and the panel at 2:00, submissions at 5:30 through the WeMakeDevs form, and presentations 5:30–6:30. Our team doc says lunch is at 1:00. Confirm at the venue.
- **Public repo, with disclosure.** The repo must be public at submission, and the README must say which AI assistants we used.
- **No personal data in the repo.** That keeps out the Chinese flashcard review history.

## The call (read this if nothing else)

1. **Pitch "Stop nodding along," not translation.** Live translation is already crowded: phones, earbuds and meeting tools all do it. Our wedge is decoding only the jargon *you personally* don't know, the moment it's said, then turning the conference into your own study plan. That personalization is both the moat and the data flywheel.
2. **Make every sponsor part of the product, not a bolt-on.** Our core promise is speed, so latency is the product:
   - **Dash0** measures word-to-card latency against an SLO.
   - **Elasticsearch's percolator** is the live jargon detector, and its hybrid search powers "Ask your conference."
   - **Gitar** custom rules enforce all of this on every PR.
   - **Radar** investigates whatever breaks in the cluster.
3. **Also enter Merge Forward (accessibility and inclusion).** Our notes skip it, yet it's our most natural fit. It serves non-native speakers, first-timers, and deaf or hard-of-hearing attendees through live captions.
4. **Cut ruthlessly.**
   - Build an installable PWA, not a native app.
   - Drop Postgres: the glossary preloads on the phone, and Elasticsearch is our only database.
   - Use managed streaming STT, not a self-hosted speech model.
   - Skip full-sentence translation; each card gets one line in the user's native language instead.
5. **Run a real demo, never a faked one.** Use live speech-to-text on a *scripted* conversation, with two phones showing two personas and different cards. If the live mic fails, replay a recording of our own rehearsal through the same real pipeline. Faking "looks live" in front of SRE and observability judges is the fastest way to lose them.
6. **Give everyone a sponsor track and a product piece.** Tanner now owns Dash0, and every product piece has an owner (see Team roles).

## Clock

Building started at 11:00, which leaves about 5 hours of real work. Each gate below has a hard definition of done.

| Time | Gate | Done means |
| --- | --- | --- |
| 11:50 | Aligned | Owners agreed. Gitar Pro trial installed. Elastic, Deepgram and Dash0 accounts created. EKS cluster creating. |
| 12:15 | Repo cleaned, skeleton live | The first PR moves pre-kickoff code out. A FastAPI hello is live over HTTPS on EKS. Screenshot Radar's first view as our "before." |
| 1:00 | **M1: walking skeleton** | Say "Kubernetes" into a phone and a caption and card appear from our URL. Traces show in Dash0. At least 3 PRs reviewed by Gitar. |
| 1:30 | Transcription test, first run | Accent fixtures plus 2 phone recordings of the talk track. All 5 must-catch terms are caught. |
| 2:00–2:30 | Lunch + Kelsey Hightower panel (confirm the time) | Eat while building. Two people watch the panel; Skyler runs the hallway survey. |
| 3:45 | **M2: demo path complete** | On both phones over cellular: probe, live cards, stage view, recap and flashcards, and search. The transcription test passes on every take. SLO dashboard live, and a Radar investigation shared. |
| 4:30 | **Feature freeze** | Bug fixes only |
| 4:30–5:15 | Rehearse 3 times | Record a clean audio take as a fallback and a 2-minute screen recording. Write the submission. |
| 5:15 | **Submit** | WeMakeDevs form. The repo is public, with a README that includes setup steps and an AI disclosure. |
| 5:30–6:30 | Presentations | Live |

## Team roles (proposed; confirm at 11:50)

Each person owns one sponsor track, one piece of the product, and the directories that piece lives in. Tanner builds the phone app, because Dash0's browser monitoring and the latency SLO live there.

| Person | Sponsor track | Product piece | Owns |
| --- | --- | --- | --- |
| Zack | Elasticsearch | The API and Elasticsearch layer: ingest, percolate, knowledge, search and recap endpoints, plus the STT `/token` endpoint | `api/`, `es/` |
| Clayton | Radar | EKS, HTTPS, ECR, CI deploy, Dash0 operator install, the Radar connection and investigation | `deploy/`, deploy workflows |
| Tanner | Dash0 | **The phone app**, with browser monitoring, the latency badge and the stage view; also the Dash0 dashboard, SLO and Agent0 loop | `web/`, `observability/` |
| Skyler | Gitar + Merge Forward | Gitar rules, CI and auto-apply; speech-to-text with keyterms and the transcription test; LLM services; glossary; **demo script, deck and submission** | `.gitar/`, `stt/`, `worker/`, `content/`, `docs/` |

Rules for parallel agents working in the same repo:

- Every directory has exactly one owner.
- Branches are named `<person>/<feature>`.
- PRs stay under 300 lines.
- Agree on API shapes in `contracts/` by 12:00. After that, change them only by PR.

## Decisions and open questions

Most questions were answered at 11:50. Two are still open, and the first needs an organizer.

| Question | Answer | What it changes |
| --- | --- | --- |
| Presentation length | Probably a few minutes, not yet confirmed | Plan a 3-minute pitch with a 2-minute cut |
| Who presents | All four of us | Each person owns one beat |
| Track owners | Clayton: Radar. Zack: Elasticsearch. Tanner: Dash0. Skyler: Gitar. | Roles table updated |
| Cloud | Everything on AWS (EKS) | Clayton sets up HTTPS, ECR and Radar on EKS |
| Repo | Keep `zackhada/confpilot` | First PR moves pre-kickoff code out, and the README explains why |
| Demo format | The two speakers talk into their own phones, and both screens are shown | Each phone decodes the other person's jargon; build a stage view |
| Must-catch terms | SRE, RAG, embed, BM25, RRF | Keyterm boosting, a normalizer, and a transcription test |
| Full-sentence translation | Dropped | One native-language line per card |
| Gitar tier | Pro trial | Custom rules and auto-apply are available |

Still open:

- [ ] Confirm the presentation length, how sponsor prizes are judged (same pitch, a booth, or the form?), and that judges read the public repo.
- [ ] Who builds the phone app? (Proposed: Tanner, because Dash0's browser monitoring lives there.)

## Stack

We keep Python and FastAPI because Zack's reference code already uses them and the team knows them. We write the ConfPilot code fresh, after kickoff.

| Piece | Choice | Why |
| --- | --- | --- |
| `app` service | FastAPI on Python 3.12, serving the API, server-sent events, and the static PWA | One service is simplest, and Python has OTel auto-instrumentation |
| PWA | Static HTML and JS with a web manifest and service worker; the glossary is cached on the phone | Installs without an app store, and lookups need no network |
| Stage view | A `/stage` page that shows both speakers' phone screens side by side from the same live feed | The projector shows both screens without mirroring cables |
| `definer` worker | Same image, different command | LLM definitions and probe extraction, run async |
| Speech-to-text | Deepgram Nova-3 streaming with keyterms, straight from each phone | Lowest latency, and keyterms protect the must-catch words |
| Data | Elastic Cloud Serverless trial (ela.st/hack-kubecon), with `semantic_text` on Jina embeddings | Elasticsearch is the core data layer |
| Deploy | GitHub Actions to ECR to EKS, behind an ALB with an ACM certificate | Every merged PR deploys itself |
| Telemetry | OTel to Dash0, Dash0 RUM in the PWA, OpenLIT for LLM calls (Dash0's own suggestion) | Covers the whole path from spoken word to rendered card |
| Secrets | A Kubernetes Secret created by a human, never in the repo | The repo will be public |
| Seed data | `content/glossary.json` plus its validator and transcript checker, run in CI | Already built and validated |

## Problem and story

The audience is already in the building: about two thirds of KubeCon attendees are first-timers, and KubeCon is down the street this week.

- **KubeCon NA 2026** runs Nov 9–12 at the Salt Palace. One vendor estimates 9,000–12,000 attendees.
- **64–73% of KubeCon attendees are first-timers.** That range covers every CNCF transparency report we checked, from 2018 to 2022.
- **64% of tech professionals report imposter syndrome**, the highest share among the sectors Hays surveyed (2025, 680 tech respondents). An informal 2018 Blind poll of 10,402 tech workers found 58%.
- **Gap: there's no hard stat on attendees who don't understand talks, so we make our own today.** At lunch, ask 10–15 people: "In the last talk you watched, did you nod along to a term you didn't actually know?" Then open the pitch with "We asked 15 people in this room, and 12 said yes." Primary data beats any citation, and it turns the judges into users.
- **Unverified:** "about 3 in 4 English speakers are non-native." Check it before it goes on a slide.

**Demo personas.** Each speaker's phone uses a profile matching their real background. Clayton knows infrastructure but not search jargon; Zack knows search but not every SRE term. A third persona, Ana, shows the onboarding map. She's a frontend developer from São Paulo at her first KubeCon. She's fictional, and we say so.

## Product: four screens, nothing else

The demo runs through four screens in this order. Anything that isn't on one of them waits until after today.

1. **Onboarding probe (about 90 seconds).** This borrows LearnHarness's method: measure before you teach, find where understanding ends, and skip what the user already knows.
   1. *Talk for 30–60 seconds:* "What do you do, and what do you want from this conference?" An LLM extracts:
      - role and domain
      - terms used correctly, which are marked known
      - a rough CEFR English level
      - goal categories
   2. *Adaptive check of 8–10 cards:* the user answers "I could explain it," "I've heard it," or "New to me," a confidence rating like LearnHarness uses. The check walks the prerequisite graph: a known term jumps to harder dependents, and an unknown term steps down to its prerequisites. In effect it's a binary search for the user's frontier.
   3. *Your map:* known terms in green, frontier in amber, beyond in grey. This screen is a strong demo moment.
2. **Live.** Big rolling captions highlight jargon as it's spoken. Cards stack in from the bottom, showing only terms this user doesn't know. At most one new card appears every 2 seconds, and the last 3 stay visible. Each card has:
   - a simple-English definition of 15 words or fewer
   - a pronunciation hint ("koo-ber-NET-eez")
   - an optional native-language line
   - a "builds on: X" chip
   - **I know this** and **Save** buttons
   - a latency badge (312 ms)
3. **Recap and flashcards.** The recap reads like "You heard 23 new terms, and RAG came up 4 times." The Learn next list ranks terms by times heard today multiplied by whether the term is on the user's frontier. Flashcards use SM-2 spaced repetition. As in the Chinese flashcard app, a term counts as learned once its review interval reaches at least 7 days.
4. **Ask your conference.** Hybrid search runs over everything the user heard, so "What did Zack say about RAG?" jumps to that moment. Multilingual embeddings mean a search in Spanish finds the English moment.

**Not today:**

- native apps
- login (a persona switcher replaces it)
- full-sentence translation
- speaker diarization
- multiple conferences
- social features
- a self-hosted speech model

LearnHarness is AGPL-3.0 licensed, so we borrow its ideas only, never its code.

## Architecture and latency

Cards come from the phone, not the server. The glossary preloads on the device, so the card for a known term appears within about 400 ms of the word being spoken. The server and the LLM only add terms the phone missed.

```
Phone (PWA, HTTPS) --mic--> Streaming STT (direct WebSocket, short-lived token from api)
  | partial transcripts
  +--> Tier 1: on-device matcher over preloaded glossary (~60 KB) -> card in <5 ms
  +--> final transcripts --> api (K8s) --> Elasticsearch
                              |-- percolate        -> Tier 2 (stems, plurals, multi-word, mis-hearings)
                              |-- index utterance  (BM25 + semantic_text)
                              |-- user-knowledge   (encounters, SRS state)
                             --> definer worker (LLM, async) -> Tier 3: unknown jargon -> new glossary entries
                             --> SSE back to phone for Tier 2/3 cards
OTel everywhere -> Dash0 (traces, logs, metrics, browser RUM, SLO)
Cluster watched by Radar (UI + MCP + AI investigations); every change lands via a Gitar-reviewed PR
```

**Latency budget.** The target is that 95% of cards render within 800 ms of the word being spoken.

- On the phone path, the STT partial takes 150–300 ms, the on-device match under 5 ms, and the render under 50 ms.
- The server path adds about 100–150 ms.
- The LLM path takes 1–3 seconds, so it always runs async and arrives as a "new term" card.

**Preloaded definitions are our "low-latency database."** Our notes ask for a fast Postgres, but the fastest store is the phone itself. The 200-term glossary (about 60 KB) ships with the app and is cached by the service worker and IndexedDB. It refreshes from the Elasticsearch `terms` index when the app opens. A lookup takes under 1 ms and needs no network, so the card appears the moment STT emits the word. Postgres would add another system and weaken the "Elastic is our core data layer" story.

**Making sure key terms are transcribed correctly.** We guard against mis-transcription in three layers:

1. **Keyterm boosting.** Each phone's STT session sends our glossary terms to Deepgram as keyterms, such as SRE, RAG, embed, BM25, RRF, Elasticsearch and Kubernetes. Amazon Transcribe's equivalent is custom vocabulary.
2. **A normalizer before matching.** STT often writes "R.R.F.", "R R F", "BM 25" or "BM twenty five." The matcher folds these into canonical forms first, and this is already built in `content/build_glossary.py`.
3. **Aliases for known mis-hearings.** Add them to the glossary as the transcription test finds them.

**Speech-to-text options.** Vendor and independent latency figures conflict, so test with our own audio in this room before 1:00.

| Option | Published latency | Verdict |
| --- | --- | --- |
| Deepgram Nova-3 / Flux | Under 300 ms (vendor); among the fastest in independent tables | **Primary.** Browser WebSocket with temporary keys. Keyterm prompting boosts our glossary terms (kubectl, RAG, Elasticsearch), which is the real win for jargon. Verify the limits. |
| ElevenLabs Scribe v2 Realtime | About 150 ms to first word (vendor, FLEURS benchmark) | Strong alternative. Skyler has an account, but with few credits. |
| AssemblyAI Universal-Streaming | About 90 ms to first word (vendor); 300–600 ms in other tests | Fine alternative |
| Amazon Transcribe streaming | About 250–800 ms | The slowest of these. Use it only if the stack must be AWS-native. |
| NVIDIA Parakeet or Nemotron on a GPU node | Very fast, self-hosted | Not today. Pitch it as the DGX Spark future: on-prem, private, no network hop. |
| Browser Web Speech API | Low; free, no key | Fallback behind a feature flag |

## Data model (Elasticsearch)

Five indices hold everything, and the user's knowledge state follows the same spaced-repetition (SRS) model as the Chinese flashcard app.

| Index | Key fields | Powers |
| --- | --- | --- |
| `terms` | term, aliases[], say (pronunciation), category, level 1–4, simple_def, long_def, example, prereqs[], translations {es, zh, hi, pt}, source (seed or llm), `semantic_text` | Cards, the knowledge graph, related terms |
| `term-queries` | One percolator query per term, covering its aliases, with analyzers | Live detection |
| `utterances` | session, speaker, ts, text plus `semantic_text`, terms[], word_to_card_ms | Search, recap, stats |
| `user-knowledge` | user + term: status (unknown, learning, known), confidence, source (probe, tap, srs), encounters, contexts[], ease, interval_days, reps, due_at, learned | Personalization, flashcards |
| `sessions` | Metadata for each talk or conversation | Recap |

**Mapping from the flashcard dataset:**

| Flashcard app | ConfPilot |
| --- | --- |
| character | term |
| pinyin | `say` |
| English meaning | `simple_def` |
| HSK level | jargon level: L1 business and idioms, L2 general tech, L3 cloud-native and AI practitioner, L4 specialist |
| review fields | the same SM-2 fields; the "learned once the interval reaches 7+ days" rule carries over |

**Make the data flywheel visible:**

- Every "I know this" tap sharpens the user's frontier.
- Every unknown term the LLM catches becomes a glossary entry for everyone.
- Pooled across users, confusion becomes a heatmap for organizers and speakers, such as "38% of your audience didn't know eBPF." That makes conferences easier for organizers too. This is a stretch goal.

## Sponsor tracks

The story to tell on stage is one closed loop: Dash0 spots a problem, Radar explains it, and Gitar ships the fix. Elasticsearch does the thinking throughout.

### Gitar (owner: Skyler)

- **Now:** Zack, as repo admin, installs the Gitar GitHub app and protects `main` so that every change needs a PR and passing CI.
- **Cadence:** every feature lands as a small PR, from humans and agents alike. Aim for 20+ PRs today, at least one per person every 45 minutes.
- **Custom rules** live in `.gitar/rules/*.md`, and review instructions in `.gitar/review/`. Our Pro trial covers custom rules. Replace the old repo's timezone rule, which was written for the talk-schedule idea. The rules encode our promises to the other sponsors:
  1. *Instrumented:* every new API route or worker handler opens an OTel span with `confpilot.*` attributes (Dash0).
  2. *K8s hygiene:* every Deployment has resource requests and limits, readiness and liveness probes, and `app.kubernetes.io/*` labels (Radar topology).
  3. *Accessible:* every control has an aria-label, tap targets are at least 44 px, color never carries meaning alone, and `prefers-reduced-motion` is respected (Merge Forward).
  4. *Glossary quality:* definitions run 20 words or fewer, in B1-level English, and never use the term to define itself. This makes Gitar review our content as well as our code.
  5. *No secrets in the client:* STT and LLM keys reach the browser only through the `/token` endpoint.
- **CI on GitHub Actions** runs lint, typecheck, matcher unit tests, the glossary schema check, axe, kubeconform, and an amd64 docker build. Real failures will happen. Let Gitar diagnose them and auto-apply the fixes, and screenshot each one.
- **Line for the pitch:** "Four humans plus a fleet of coding agents shipped N PRs in five hours. Gitar was our tech lead."

### Dash0 (owner: Tanner; each service owner adds their own spans)

- **The north-star SLI is word-to-card latency.** The SLO is that 95% of cards render in under 800 ms. It appears on a Dash0 dashboard and as the badge on every card, so observability shows up inside the product itself.
- **Instrumentation:**
  - The Dash0 Kubernetes operator provides the OTel collector and auto-instrumentation.
  - Custom spans cover `stt.token`, `utterance.ingest`, `es.percolate`, `llm.define` and `card.push`.
  - Browser RUM passes `traceparent` from the phone to the API, giving one trace from spoken word to rendered card.
  - Metrics track cards per minute, unknown-term rate, LLM fallback rate and STT reconnects.
- **The Agent0 + MCP loop, our best story:** connect the Dash0 MCP to Claude Code. When p95 drifts, ask Agent0 why. Something will be slow, such as the LLM sitting in the request path or a cold Elastic query. The fix lands as a PR that Gitar reviews, and Dash0 shows latency drop. Capture before and after, and show it in the demo, since the judging criteria ask for that.

### Radar (owner: Clayton)

- **Cluster: EKS on Clayton's AWS account (decided).** Public HTTPS runs through an ALB with an ACM certificate. Images go to ECR, and GitHub Actions deploys on every merge to `main`. Radar's team vcluster stays the fallback.
- **Connect Radar.** Connect the EKS cluster to the hackathon's Radar Cloud org, or run `kubectl radar` locally. Add the MCP to every agent with `claude mcp add --scope user radar-cloud --transport http https://api.radarhq.io/mcp`. Use it all day to ship, check rollouts, and read issues.
- **Before and after.** Screenshot Radar's Checks or Issues view in the first hour as our "before," then again at the end.
- **A real investigation.** Run Radar Investigate on the first real failure, such as a CrashLoopBackOff from a missing secret, an OOMKilled worker, or a wrong image architecture. Save the Findings, then fix the cause with a Gitar-reviewed PR. Don't break anything on purpose, and don't use the repo's pre-planned `oom-fix` overlay. If nothing breaks, investigate after a release; an all-clear with evidence counts.
- **Share it.** Investigations start private, so whoever started one must present it or mark it Shared.
- **Pitch story.** Tell it with Radar's timeline, the investigation, and the before-and-after view. Radar's agent can draft this "5:30 story."

### Elasticsearch (owner: Zack)

- **Use the free Elastic Cloud Serverless trial (ela.st/hack-kubecon), Elasticsearch project type.** The Elastic Inference Service is on by default, so `semantic_text` works with no ML setup. Don't run Elasticsearch inside our cluster today.
- **Show smart use, not just storage:**
  1. The percolator detects jargon live: each term is stored as a query, and each utterance is percolated against them.
  2. Hybrid search powers Ask your conference, combining BM25 and `semantic_text` with the RRF retriever.
  3. Multilingual semantic search lets a question asked in Spanish find the English moment. Confirm the embedding model is multilingual, because ELSER is English-only.
  4. Vector similarity finds related terms and places new LLM-found terms in the graph.
  5. Aggregations feed the recap and the confusion heatmap.
- **Stretch, only once items 2–4 are done:** Elastic Agent Builder for Ask.

### Merge Forward (owner: Skyler; Tanner builds the UI)

The product already serves inclusion, so the job is to show the craft:

- captions that double as live captioning for deaf and hard-of-hearing attendees
- large type, high contrast and dark mode
- screen-reader labels and haptic feedback on new cards
- reduced motion
- a native-language line and pronunciation hints
- axe checks in CI, enforced by Gitar rule 3

### Best Overall (DGX Spark)

Polish and story decide this prize. The vision slide: "With a DGX Spark at the venue, speech recognition and the LLM run on-prem: private, offline, and instant for every attendee."

## Demo and pitch

The pitch runs 3 minutes, and all four of us speak. Rows marked "(cut)" come out if we only get 2 minutes.

**Setup:**

- **Clayton and Zack each talk into their own phone**, as the team doc asks. Each phone captures its owner's voice clearly and runs its own STT stream into a shared room. Both phones then show the whole conversation with speaker labels.
- **Each phone decodes the other person's jargon.** Clayton's phone explains Zack's search terms (BM25, RRF, embeddings), and Zack's phone explains Clayton's SRE and Kubernetes terms. That is our problem statement solved on stage: two people who would talk past each other now understand each other.
- **Show both screens at once.** The primary option is a `/stage` page on the laptop that renders both phone screens side by side from the same live feed, readable at projector size. For literal mirroring, use QuickTime's New Movie Recording with each iPhone over USB, one window per phone. Test both at lunch with the HDMI dongle.
- **The phones run on a cellular hotspot**, not venue wifi.

| Time | Beat | Who |
| --- | --- | --- |
| 0:00 | Ask for a show of hands: "Who's nodded along to a word they didn't know?" Then give the lunch survey result and the 64–73% first-timers stat. | Skyler |
| 0:20 | (cut) A newcomer's onboarding map, run beforehand | Tanner |
| 0:30 | **Live conversation** (script below, about 55 seconds). Both screens are on the projector, and each phone decodes the other speaker's jargon. | Clayton + Zack |
| 1:30 | Each speaker's recap: new terms heard, Learn next, and a flashcard flip. (cut) A Spanish search finds Zack's RRF explanation. | Tanner |
| 2:00 | Under the hood, about 10 seconds each: Gitar PRs and auto-apply (Skyler), the Dash0 SLO and Agent0 fix (Tanner), the Radar investigation (Clayton), and the Elastic percolator with hybrid search (Zack) | Each owner |
| 2:45 | Close on the data flywheel, the organizer heatmap and the DGX Spark vision, ending with "Stop nodding along." | Skyler |

**Conversation script (the team's track, about 55 seconds).** Checked against the glossary, it triggers 23 cards across 19 terms, including all five must-catch terms. It leans heavily on search, so Zack's phone will show few cards. One optional Clayton line, shown last below, would balance the two screens.

> **Clayton:** I work at Radar, we do SRE for Kubernetes clusters. What do you do?
>
> **Zack:** I work at Elasticsearch, we do managed hybrid search, including RAG and keyword search.
>
> **Clayton:** Nice! So that will help power apps' search engines, or what are customers trying to do with your technology?
>
> **Zack:** Yeah, for sure! Wikipedia is one of our customers. Nowadays, a lot of our customers are using our product to embed thousands of documents into a knowledge base the agent can pull from.
>
> **Clayton:** Interesting, so those documents are turned into vectors that can be retrieved easily. How does your search service determine what is most relevant to the agent or user's query?
>
> **Zack:** Great question! It uses BM25 for keyword matches, while the embeddings handle meaning, and RRF to rank the results to return to the user or agent.
>
> **Clayton:** Oh, makes sense! At Radar, we have some internal search service use cases. Can I get your LinkedIn?
>
> *Optional balance line, for Clayton after Zack's first answer:* "Nice. On our side, when a pod goes into CrashLoopBackOff, our AI SRE finds the root cause before the on-call engineer wakes up."

**Fallbacks, in order:**

1. Live mic.
2. Play the rehearsal recording through the same pipeline, with real STT and real cards. Say so if we use it.
3. The 2-minute screen recording.

## Transcription test (owner: Skyler)

The five must-catch terms are SRE, RAG, embed, BM25 and RRF. A take passes only if all five are caught, and the demo needs every take to pass.

1. **Fixtures.** `content/stt-fixtures/talk_track.txt` holds the talk track, and `content/make_fixtures.sh` renders it in seven synthetic English accents: two Indian, British, Australian, Irish, South African and US. Audio stays out of git. Add 2–3 real takes recorded on each speaker's own phone in the venue, since those matter most.
2. **Run.** `DEEPGRAM_API_KEY=... content/stt_test.sh` sends each take to Deepgram with the same model and keyterms as the app. It then scores the transcripts with `python3 content/build_glossary.py --check` and exits with an error if any must-catch term is missed, so it can run in CI.
3. **Fix what it finds.** Each miss becomes a new keyterm or a glossary alias, landed through a Gitar-reviewed PR.
4. **Final check.** Before the demo, replay one real take through the live streaming path on both phones. That proves the whole chain, from audio to card.

The checker also flagged a false positive: in "search service," the word "service" matched the Kubernetes Service term. Terms marked `ambiguous` in the glossary need nearby tech context before a card pops.

**Baseline result (12:15): local Whisper small.en, no keyterm boosting, synthetic voices.** Five of seven accents caught all five must-catch terms. RAG is the risk.

| Voice | Must-catch terms | Talk-track terms | What went wrong |
| --- | --- | --- | --- |
| Daniel (UK) | 5/5 | 19/19 | Nothing |
| Karen (Australia) | 5/5 | 19/19 | Nothing |
| Moira (Ireland) | 5/5 | 19/19 | Nothing |
| Samantha (US) | 5/5 | 19/19 | Nothing |
| Tessa (South Africa) | 5/5 | 19/19 | Nothing |
| Rishi (India) | 4/5 | 18/19 | RAG heard as "drag" |
| Aman (India) | 4/5 | 17/19 | RAG heard as "our AG"; "managed" heard as "manage" |

These scores already include one fix. Before it, Elasticsearch came out as "ElasticSarc," "ElasticSuck" or "ElasticSock" in 5 of 7 voices; a new normalizer rule now maps those back to Elasticsearch.

What to do about RAG:

- **Boost it.** Send "RAG" as a Deepgram keyterm, then rerun `stt_test.sh` to confirm the keyterms fix it. Whisper is only the free local baseline; Deepgram is the production path.
- **Say it twice in the demo.** Have Zack say "RAG, retrieval-augmented generation." The long form also triggers the RAG card, so one mis-hearing can't lose it.
- **Don't add "drag" as an alias.** It's a common word and would pop false cards.

## Submission checklist and risks

Sponsor judges will want to see proof, not just hear about it, so every track needs links and screenshots in the README.

- [ ] README covering:
  - a one-paragraph pitch
  - the architecture diagram
  - how to run it
  - a section per sponsor with links and screenshots: Gitar PRs and rule files, the Dash0 dashboard, SLO and Agent0 thread, Radar Findings, and the Elastic mappings and queries
- [ ] A 2-minute demo video
- [ ] A public repo, as the rules require, with an AI disclosure in the README (Codex, DeepSeek, Claude Code). Every teammate must be able to explain the architecture.
- [ ] Credits and license. Take ideas only from LearnHarness, which is AGPL-3.0.
- [ ] Privacy line: audio is never stored, transcripts are opt-in, and the demo conversation has everyone's consent.

| Risk | Mitigation |
| --- | --- |
| Must-catch terms mis-transcribed | Keyterm boosting, the normalizer, and the transcription test on every take |
| Pre-kickoff code judged as our work | The first PR moves it out, and the README explains |
| Venue noise or wifi | Each speaker talks into their own phone; cellular hotspot; recorded-audio fallback |
| iOS mic, HTTPS or PWA quirks | Test on a real iPhone by 1:00. Fall back to a Safari tab instead of the home-screen app. |
| Image architecture vs EKS nodes | CI builds for the node architecture |
| Agents colliding in the repo | Directory ownership, contracts agreed first, small PRs |
| A slow LLM in the hot path | Keep the LLM async, always |
| Scope creep | At the 3:45 gate, anything that doesn't work gets cut, not fixed |

## Sources

- [CNCF: KubeCon NA 2026 schedule announcement](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/)
- CNCF transparency reports: [NA 2018 (73% first-timers)](https://cncf.io/blog/2019/02/12/kubecon-cloudnativecon-north-america-2018-conference-transparency-report-a-record-breaking-cncf-event), [NA 2019 (65%)](https://cncf.io/blog/2020/01/09/kubecon-cloudnativecon-north-america-2019-conference-transparency-report-the-biggest-kubecon-cloudnativecon-to-date), [NA 2022 (64%)](https://cncf.io/reports/kubecon-cloudnativecon-north-america-2022-transparency-report)
- [Hays 2025 imposter syndrome research](https://www.hays.co.uk/media-centre/press-releases/content/hays-research-imposter-syndrome-women-in-tech) and the [Blind 2018 poll](https://www.teamblind.com/blog/58-percent-of-tech-workers-feel-like-impostors)
- STT latency comparisons, which use conflicting methods: [Coval](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/), [FutureAGI](https://futureagi.com/blog/speech-to-text-apis-in-2026-benchmarks-pricing-developer-s-decision-guide/), [Gradium](https://gradium.ai/content/stt-api-benchmark-2026-latency-accuracy)
- [Radar (skyhook-io/radar)](https://github.com/skyhook-io/radar)
- [Gitar rules repo](https://github.com/gitarcode/rules) and [Sonar's Gitar blueprint](https://www.sonarsource.com/developers/blueprints/scale-gitar-context-across-an-organization/)
- Dash0: [MCP server](https://www.dash0.com/changelog/dash0-mcp-server), [Kubernetes operator](https://www.dash0.com/documentation/dash0/dash0-kubernetes-operator), [SLOs](https://www.dash0.com/changelog/service-level-objectives-are-now-available)
- Elastic: [hybrid search with semantic_text](https://www.elastic.co/docs/solutions/search/hybrid-semantic-text), [Jina models on EIS](https://www.elastic.co/search-labs/en/blog/jina-rerankers-elastic-inference-service)
- [LearnHarness](https://github.com/amosblomqvist/learnharness)
