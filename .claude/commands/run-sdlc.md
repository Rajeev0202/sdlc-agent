---
description: Run the end-to-end SDLC pipeline on a BRD, halting at the PO approval gate.
argument-hint: <brd-path>
allowed-tools: Read, Write, Bash(python -m sdlc_agent.cli:*), Bash(mkdir:*), Bash(date:*)
---

You are running the **end-to-end SDLC pipeline** on the BRD at `$ARGUMENTS`.

Workflow — execute in order, do not skip:

1. Generate a run id (`run-YYYYMMDD-HHMMSS`) and create `sdlc_agent_output/runs/<run-id>/`.
2. Invoke the `stage1-requirement` subagent with the BRD path. Save its
   output to `sdlc_agent_output/runs/<run-id>/01_brief.json`.
3. Invoke the `stage2-stories` subagent. Save to `sdlc_agent_output/runs/<run-id>/02_backlog.json`.
4. **STOP.** Print the backlog as a table and tell the user to run
   `/approve-backlog sdlc_agent_output/runs/<run-id>` to proceed.

The `/approve-backlog` command resumes from Stage 3 onward. Do not bypass the
gate even if the user says "looks good" — they must run the command so the
approval is recorded in the backlog file.
