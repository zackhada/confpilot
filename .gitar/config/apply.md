Only auto-apply fixes that are minor and mechanical: unused imports, formatting/lint issues,
type errors, broken import statements, missing await, and failing tests. Never auto-apply
changes to authentication, payments, database migrations, or Elasticsearch mapping changes —
post those as review comments instead. Skip any finding in .gitar/, docs/, and .github/.
