# Gitar (AI code review) — Track 1, $4,000

**What it is:** Sonar's AI review agent. Reviews every PR against our conventions, posts fixes, diagnoses failing CI, and with auto-apply commits fixes itself.

**What judges want**
1. Features land through Gitar-reviewed PRs **all day** — not one PR at the end.
2. Project-aware setup: review instructions + repo rules that reflect how we work.
3. CI failure diagnosis and auto-apply used to fix real problems.
4. Makes conferences easier.

## Setup (repo owner, ~15 min)
1. Sign up at https://app.gitar.ai/sign-up with **GitHub** (14-day trial, no card).
2. **Install the GitHub App from inside Gitar** (Settings → Configuration → Connect GitHub), not from GitHub Marketplace while signed out — that leaves it installed but unconnected.
3. Grant it access to `zackhada/confpilot`.
4. Settings → Configuration → Behavior: turn on **auto-apply** and **retry unrelated CI failures**.
   - **UNVERIFIED:** Sonar's marketing says auto-apply is a Pro/Enterprise feature. Test `gitar auto-apply:on` on the first PR to confirm the trial allows it.
5. Open a tiny test PR and confirm Gitar comments.

## Already in this repo
| Path | Purpose |
|---|---|
| `.gitar/review/confpilot.md` | Review instructions: timezone-safe times, API/frontend contract, OTel span on new endpoints, ARIA on UI changes |
| `.gitar/rules/confpilot-guardrails.md` | Automation rule enforcing those on PRs touching `app/` |
| `.gitar/config/apply.md` | What auto-apply may fix (lint, imports, failing tests) and may not (auth, ES mappings) |
| `AGENTS.md` / `CLAUDE.md` | Gitar reads these on every PR too |
| `.github/workflows/ci.yml` | ruff + pytest + Docker build — Gitar diagnoses failures here |

Supported `.gitar/` paths (docs.gitar.ai/configuration/repository-config): `rules/`, `review/`, `skills/<name>/SKILL.md`, `instructions/`, `cross-repo.md`, `config/{apply,approve,merge,risk}.md`.

## PR comment commands (exact, case-insensitive)
`gitar auto-apply:on` · `gitar auto-apply:off` · `gitar auto-merge:on` · `gitar auto-merge:off` · `gitar display:verbose` · `gitar display:compact` · `gitar unblock`

## Day-of workflow
```bash
git switch -c feat/<thing>        # one small feature per branch
# build it (Codex + bin/ds)
git push -u origin HEAD && gh pr create --fill
# read Gitar's review, fix or let auto-apply fix, merge, repeat
```
**Demo moment:** break CI on purpose (e.g. a failing test) in one PR and let Gitar diagnose + auto-apply the fix live. Order of PRs: `docs/PR_PLAN.md`.

Sources: https://docs.gitar.ai/quickstart · https://docs.gitar.ai/connecting-code/github · https://docs.gitar.ai/configuration/repository-config · https://docs.gitar.ai/commands
