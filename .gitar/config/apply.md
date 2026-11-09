Auto-apply only fixes that are minor and mechanical: unused imports, formatting and lint
issues, type errors, broken import statements, a missing await (never in the live card or transcript path, where LLM calls must stay
unawaited), and failing tests whose fix is obvious from the failure. Never auto-apply changes to `contracts/`, Elasticsearch mappings
in `es/`, Kubernetes manifests in `deploy/`, anything that handles secrets or tokens, or the
glossary content. Post those as review comments instead. Skip findings in `.gitar/`, `docs/`,
`.github/` and `reference/`.
