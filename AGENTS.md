# ConfPilot: agent instructions

ConfPilot decodes the jargon each attendee doesn't know, live, then turns the conference into
their study plan. Read `docs/CONFPILOT_PLAN.md` before any work; it is the source of truth.
Hackathon rules and judging criteria: `docs/HACKATHON.md`.

## Hard rules

- **Never use `reference/`.** It is pre-kickoff code for a different idea. Do not import it,
  copy from it, build it or deploy it. Write ConfPilot code fresh.
- **Every change lands as a small PR** (under 300 changed lines), reviewed by Gitar, with CI
  green. Branches are named `<person>/<feature>`. Never push to `main`.
- **One owner per directory** (see README). Parallel agents never touch the same files.
- **API and event shapes live in `contracts/`.** Change them only by PR, and update every
  consumer in the same PR.
- **No secrets in the repo or in browser code.** Keys reach the browser only through the
  `/token` endpoint. The repo will be public.
- **No personal data in the repo.**
- **Nothing staged or faked.** Do not break things on purpose for the demo, and do not use
  the old `oom-fix` overlay.

## Conventions

- Every new API route or worker handler opens an OpenTelemetry span with `confpilot.*`
  attributes.
- Every Deployment has resource requests and limits, readiness and liveness probes, and
  `app.kubernetes.io/*` labels.
- Every UI control has an accessible name, tap targets are at least 44 px, color never carries
  meaning alone, and `prefers-reduced-motion` is respected.
- Glossary definitions are 20 words or fewer, in plain (B1) English, and never use the term to
  define itself.
- The LLM never sits in the request path; it always runs async.
- Elasticsearch is the only database.

## Layout

`contracts/` shapes · `api/` FastAPI · `es/` mappings and queries · `web/` phone app and stage
view · `deploy/` EKS · `content/` glossary · `docs/` plan and setup ·
`reference/` do not use
