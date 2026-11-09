# ConfPilot review instructions

ConfPilot decodes the jargon each conference attendee doesn't know, the moment it is said,
then turns the conference into their study plan. A phone app (PWA in `web/`) streams speech
to text, matches jargon on the device, and talks to a FastAPI service (`api/`) over one
WebSocket per phone. Elasticsearch is the only database. The promise is speed: 95% of cards
render within 800 ms of the word being spoken. Review every PR against that promise and
against the five rules below. Shapes are defined in `contracts/`.

## 1. Instrumented (Dash0)
- Every new or changed API route, WebSocket handler and worker handler opens an
  OpenTelemetry span and sets `confpilot.*` attributes (for example `confpilot.room`,
  `confpilot.card.tier`).
- Elasticsearch, speech-to-text token and LLM calls each get their own child span.
- Flag handlers that do I/O with no span, and `except` blocks that swallow an error without
  recording it on the span.

## 2. Nothing slow in the card path
- The LLM is never awaited in a request or WebSocket handler that produces live cards. It
  runs async and delivers its result as a later `card` event.
- A `transcript` event is relayed to the room before any storage or search work.
- Cards are never queued or delayed in the UI; animation must not postpone the first paint.
- Flag any `await` of an LLM or a slow network call added to the transcript relay path.

## 3. Kubernetes hygiene (Radar)
- Every Deployment has resource requests and limits, readiness and liveness probes, and
  `app.kubernetes.io/name`, `app.kubernetes.io/component` and `app.kubernetes.io/part-of`
  labels.
- The API Deployment stays at one replica, because the room hub is in memory.
- Nothing is broken on purpose. Flag any staged failure, chaos switch or deliberately low
  limit.

## 4. Accessible (Merge Forward)
- Every interactive control has an accessible name and is keyboard operable.
- Tap targets are at least 44 px. Color never carries meaning on its own.
- Captions and new cards are announced through an `aria-live` region.
- Animation uses transform and opacity only, and respects `prefers-reduced-motion`.

## 5. Glossary quality
- `simple_def` is 15 words or fewer, in plain (B1) English, and never uses the term to
  define itself.
- Every `prereqs` id exists in the glossary, and there are no prerequisite cycles.
- Common words are never added as aliases (for example "drag" for RAG). A term that is also
  a common word must be marked `ambiguous` with `context` words.

## 6. Secrets and contracts
- Speech-to-text and LLM keys reach the browser only through `POST /api/token`. Flag any key,
  token or `Authorization` value in `web/`, in a manifest, or in a workflow file.
- A PR that changes a shape in `contracts/` updates every consumer in the same PR.
- Nothing outside `reference/` imports, copies or builds code from `reference/`. That folder
  is pre-kickoff code and is not part of the submission.

## How the team works
- PRs stay under 300 changed lines and do one thing.
- Each directory has one owner (see the README). Flag a PR that edits another owner's
  directory without saying why.
- Logic changes come with a test in the same PR.
