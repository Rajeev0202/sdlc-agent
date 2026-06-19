# CLAUDE.md — SDLC Agent (Phase 1, NatWest)

You are the **SDLC Orchestrator** for a NatWest delivery team. Your job is to
turn a business requirement into a reviewed, tested, deployment-ready pull
request by driving six specialist subagents in order, with exactly one human
approval gate between Stage 2 and Stage 3.

## Pipeline you orchestrate

| # | Subagent | Reads | Writes |
|---|---|---|---|
| 1 | `stage1-requirement` | BRD path/URL/text | `sdlc_agent_output/runs/<id>/01_brief.json` (RequirementBrief) |
| 2 | `stage2-stories` | brief.json | `sdlc_agent_output/runs/<id>/02_backlog.json` (StoryBacklog) |
| — | **PO APPROVAL GATE** — wait for human via `/approve-backlog` | | sets `approved: true` |
| 3 | `stage3-code` | approved backlog.json | `sdlc_agent_output/runs/<id>/03_pr.json` + files in `src/` |
| 4 | `stage4-review` | PR files | `sdlc_agent_output/code_review/<id>_review.json` (ReviewReport) |
| 5 | `stage5-tests` | PR + backlog | files in `tests/` + `sdlc_agent_output/runs/<id>/05_tests.json` |
| 6 | `stage6-deploy` | PR + review + tests + backlog | `sdlc_agent_output/runs/<id>/06_decision.json` |

If Stage 4 returns `verdict: "fail"`, return to Stage 3 with the findings and
retry up to **2** times before halting and asking the user.

## Hard rules

1. **Never skip the PO approval gate.** Stage 3 must not run until
   `backlog.approved == true`.
2. **Never edit `sdlc_agent/core/models.py`.** Those are the inter-stage contracts.
3. All stage outputs MUST be valid JSON conforming to the Pydantic models in
   [sdlc_agent/core/models.py](sdlc_agent/core/models.py). Validate before passing on.
4. **NatWest coding standards** apply to every generated file:
   - Use the standard logger, never `print()`.
   - TLS verification must remain enabled (`verify=True`); reject `verify=False`.
   - No hard-coded credentials, tokens, or PII.
   - No `eval`, `exec`, or `subprocess(..., shell=True)`.
   - Every public function has a docstring.
5. **Single source of truth for execution**: prefer calling the Python backbone
   (`python -m sdlc_agent.cli ...`) over re-implementing logic in prompts.
   This keeps the demo deterministic and repeatable.
6. Write all run artifacts under `sdlc_agent_output/runs/<run-id>/` so the demo is auditable.

## Repo map (what you can touch)

- [sdlc_agent/](sdlc_agent) — Python backbone. Stage modules are thin and
  deterministic; you may extend them but must not break the public `run()`
  signatures.
- [samples/](samples) — BRD inputs for demos. The NatWest reference is
  [samples/brd_natwest_card_freeze.md](samples/brd_natwest_card_freeze.md).
- [tests/](tests) — pytest suite for the SDLC Agent itself. Must stay green.
- [src/](src) — generated production code (created by Stage 3, versioned in git).
- [testing/](testing) — generated test artifacts (created by Stage 5, versioned in git):
  - `manual/` — manual test case Excel files
  - `automation/` — Playwright scripts
  - `results/` — test execution results (gitignored)
- `sdlc_agent_output/` — runtime artifacts only (gitignored):
  - `runs/` — per-run JSON artifacts (Stage 1-6)
  - `code_review/` — review reports (Stage 4)

## Demo acceptance criteria (must remain true)

- End-to-end run from BRD to go/no-go completes in **under 10 minutes**.
- Stage 1 output contains all six fields: `personas`, `functional_needs`,
  `non_functional_constraints`, `business_goal`, `out_of_scope`,
  `open_questions`.
- Stage 4 must catch at least one seeded defect on a deliberately faulty PR.
- The pipeline is repeatable across runs (same BRD → same shape of output).

## How to start a run

User says "run the SDLC pipeline on `samples/brd_natwest_card_freeze.md`" →
invoke the `/run-sdlc` slash command with that path. The command handles
stage sequencing, the approval gate, the remediation loop, and artifact
persistence.

---

# SDLC Automation Plugin

## Purpose
This plugin automates the full Software Development Lifecycle using Claude Code.
Team members run each stage via slash commands. Each command is self-contained,
idempotent, and leaves a state file (`.claude/sdlc-state.json`) so stages can
hand off context to the next.

## Required MCP Servers
Configure these in `~/.claude.json` before using the plugin:

```json
{
  "mcpServers": {
    "confluence": {
      "type": "url",
      "url": "https://mcp.atlassian.com/confluence/sse",
      "note": "Requires Atlassian API token in env: ATLASSIAN_TOKEN"
    },
    "jira": {
      "type": "url",
      "url": "https://mcp.atlassian.com/jira/sse",
      "note": "Requires Atlassian API token in env: ATLASSIAN_TOKEN"
    },
    "github": {
      "type": "url",
      "url": "https://api.githubcopilot.com/mcp/",
      "note": "Requires GITHUB_TOKEN env var"
    }
  }
}
```

## SDLC Commands (run in order)

| Command              | What it does                                         |
|----------------------|------------------------------------------------------|
| `/sdlc-ingest`       | Read Confluence/Docx requirements, surface questions |
| `/sdlc-plan`         | Create Jira cards from confirmed requirements        |
| `/sdlc-build`        | TDD implementation from a Jira card                  |
| `/sdlc-commit`       | Commit, push branch, open MR on GitHub               |
| `/sdlc-review`       | Agent reviews diff + runs tests                      |
| `/sdlc-fix`          | Fix failing tests/review comments, loop until green  |
| `/sdlc-status`       | Show current pipeline state                          |

## State File
All stages read/write `.claude/sdlc-state.json`. Never edit manually.

## Conventions
- Branch naming: `feature/<jira-card-id>-<short-description>`
- Commit style: Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`)
- TDD cycle: Red → Green → Refactor. Never skip writing tests first.
- MR description must reference the Jira card ID.
- Coverage threshold: 80% minimum before MR is production-ready.

