---
title: "ConfPilot guardrails"
description: "Enforce timezone, contract, OTel, and accessibility conventions on ConfPilot PRs"
type: check
when: "Any PR that modifies app/ (backend), the frontend, or adds/changes an /api endpoint"
actions: "Post a checklist comment and add a needs-review label when a required convention is missing"
---

When a PR touches the backend or frontend:
- Verify every datetime returned to the client is UTC and timezone-aware (IANA zones).
- Verify any /api change updates the Pydantic schema, OpenAPI doc, and frontend fetcher together.
- Verify new endpoints emit an OTel span (auto or manual) with useful attributes.
- Verify UI changes include ARIA labels, aria-live for dynamic content, keyboard operability,
  and plain-language summaries.
- If any of these are missing, post a comment listing exactly what is missing and add the
  `needs-review` label.
- Skip this check for PRs that only touch docs/, .github/, or .gitar/.
