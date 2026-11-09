# Codex + DeepSeek subagents (how we build)

Codex is the lead (plans, reviews, merges). DeepSeek V4 Pro agents do the heavy lifting via the `pi` CLI.

```bash
cd ~/Desktop/confpilot && codex          # Codex reads AGENTS.md automatically
bin/ds "task"                            # run a DeepSeek subagent, wait, print summary
bin/ds -b -n search "task"               # background
bin/ds-status                            # running / finished; logs in .agents/logs/
```

- DeepSeek access is via the **opencode-go** plan in `~/.pi/agent`. It hit its usage limit on Nov 8 — run `bin/ds "say ok"` in the morning to confirm it reset. If not, Codex does the work itself.
- Teammates without `pi`: just use Codex/Claude Code directly; `bin/ds` is optional.
- At the event every attendee gets **$50 OpenAI credits** — use for Codex and for the app's LLM (`LLM_BASE_URL=https://api.openai.com/v1`, `LLM_API_KEY`, `LLM_MODEL`).

Connect MCP servers so Codex can see live data (details in DASH0.md and RADAR.md):
```bash
codex mcp add dash0 --url https://api.us-west-2.aws.dash0.com/mcp && codex mcp login dash0
codex mcp add radar --url http://localhost:9280/mcp-readonly
```
