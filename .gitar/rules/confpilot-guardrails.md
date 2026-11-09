---
title: "ConfPilot guardrails"
description: "Check the speed, instrumentation, Kubernetes, accessibility and secrets promises on every code PR"
type: check
when: "Any PR that modifies api/, web/, worker/, stt/, es/, deploy/, content/ or contracts/"
actions: "Post a checklist comment listing each missing item, and add the needs-review label when any item is missing"
---

Check only the parts the PR touches:

- **api/, worker/, stt/**: every new or changed route or handler opens an OpenTelemetry span
  with `confpilot.*` attributes. No LLM call is awaited in the live card or transcript path.
- **web/**: every control has an accessible name, tap targets are at least 44 px, color is
  never the only signal, animation respects `prefers-reduced-motion`, and no key or token is
  present in client code.
- **deploy/**: every Deployment has resource requests and limits, readiness and liveness
  probes, and `app.kubernetes.io/*` labels. The API has exactly one replica. No secret values.
- **content/**: every `simple_def` is 15 words or fewer and does not use its own term. Every
  `prereqs` id exists. No common word is added as an alias.
- **contracts/**: every consumer of a changed shape is updated in the same PR.
- **anywhere**: nothing outside `reference/` uses code from `reference/`.

If everything passes, post a one-line confirmation. Skip PRs that only touch `docs/`,
`.github/` or `.gitar/`.
