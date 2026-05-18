---
description: Mark a Stage-2 backlog as PO-approved and run Stages 3–6 to completion.
argument-hint: <run-dir>
allowed-tools: Read, Write, Edit, Bash(python -m sdlc_agent.cli:*), Bash(pytest:*)
---

Run directory: `$ARGUMENTS` (e.g. `runs/run-20260515-101530`).

Steps:

1. Read `$ARGUMENTS/02_backlog.json`. Set `approved: true`,
   `approver: "<current user>"`, `approved_at: <ISO timestamp>`.
   Write the file back.
2. Invoke `stage3-code`. Save PR descriptor to `$ARGUMENTS/03_pr.json`.
3. Invoke `stage4-review`. Save to `$ARGUMENTS/04_review.json`.
4. If `verdict == "fail"`, re-invoke `stage3-code` in remediation mode with
   the review findings. Retry up to **2** times. If still failing after that,
   HALT and report the blocking findings to the user.
5. Invoke `stage5-tests`. Save to `$ARGUMENTS/05_tests.json`. Run `pytest -q`
   and ensure it is green.
6. Re-invoke `stage4-review` once more so the coverage gate clears, then
   invoke `stage6-deploy`. Save to `$ARGUMENTS/06_decision.json`.
7. Print the release note from `$ARGUMENTS/RELEASE_NOTES.md` and the final
   GO / NO-GO verdict.

Total wall-clock budget: **under 10 minutes**. If any single stage exceeds
3 minutes, abort and surface the bottleneck.
