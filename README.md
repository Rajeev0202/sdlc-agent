# SDLC Agent — Phase 1 (Claude Code)

End-to-end Software Delivery Lifecycle agent that turns a business requirement
into a reviewed, tested, deployment-ready pull request. Phase 1 targets the
**Claude Code** platform (NatWest scenario) with one human approval gate
between Stage 2 (story sign-off) and Stage 3 (code generation).

## Pipeline

```
BRD ─► [1] Requirement ingestion
        │
        ▼
       [2] User-story generation ──► PO APPROVAL GATE
                                       │
                                       ▼
                                      [3] Code generation
                                       │
                                       ▼
                                      [4] Code review ◄──┐
                                       │ (fail)         │
                                       ├────────────────┘
                                       ▼ (pass)
                                      [5] Test generation
                                       │
                                       ▼
                                      [6] Deployment readiness
                                       │
                                       ▼
                                     Go / No-go + release note
```

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m sdlc_agent.cli run --brd samples/brd_payment_limits.md
```

The default run uses **mocked LLM and integration clients** (Jira, Confluence,
GitHub, Anthropic). Real clients can be wired in by replacing the implementations
in `sdlc_agent/integrations/`.

## Running it as a Claude Code agent

The repo is also wired up as a native Claude Code agent. Install the CLI once:

```powershell
npm install -g @anthropic-ai/claude-code
$env:ANTHROPIC_API_KEY = "sk-ant-..."
cd "path\to\SDLC_Agent"
claude
```

Inside the Claude Code REPL:

```
> /run-sdlc samples/brd_natwest_card_freeze.md
# (review the backlog table it prints)
> /approve-backlog runs/<run-id>
```

What you get:
- [CLAUDE.md](CLAUDE.md) — project memory: rules, gates, NatWest standards.
- [.claude/agents/](.claude/agents) — one subagent per SDLC stage with a
  scoped tool allowlist (read-only for review, write-restricted to `src/`
  for code, etc.).
- [.claude/commands/](.claude/commands) — `/run-sdlc` and `/approve-backlog`
  slash commands that enforce the human approval gate.
- [.claude/settings.json](.claude/settings.json) — permission policy
  (denies edits to `models.py`, denies `git push`, denies network calls).
- [.mcp.json](.mcp.json) — commented MCP server stubs for Jira, Confluence,
  GitHub. Uncomment + set env vars when you're ready for real systems.

Each subagent shells out to the deterministic Python backbone
(`python -m sdlc_agent.cli ingest|stories|code|review|tests|deploy`) so the
demo is reproducible across runs.

## Layout

| Path | Purpose |
|------|---------|
| [sdlc_agent/stages](sdlc_agent/stages) | One module per SDLC stage (1–6) |
| [sdlc_agent/orchestrator.py](sdlc_agent/orchestrator.py) | Runs the pipeline + approval gate |
| [sdlc_agent/integrations](sdlc_agent/integrations) | Mocked Jira / Confluence / GitHub / Anthropic clients |
| [sdlc_agent/models.py](sdlc_agent/models.py) | Pydantic data contracts between stages |
| [sdlc_agent/cli.py](sdlc_agent/cli.py) | Typer CLI entrypoint |
| [samples/](samples) | Example BRD inputs |
| [tests/](tests) | Stage smoke tests |

## Phases (roadmap)

- **Phase 1** — Claude Code agent (this repo)
- **Phase 2** — Same use case re-implemented in Codex
- **Phase 3** — Three-agent orchestration (Nemotron + Codex + Claude)
