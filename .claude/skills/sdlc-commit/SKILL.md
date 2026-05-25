---
description: SDLC Stage 4 — Commit all changes with a semantic message, push the feature branch, and open a Pull Request on GitHub pre-filled from the Jira card. Invoke with /sdlc-commit.
allowed-tools: Read, Write, Bash, mcp__github__create_pull_request, mcp__github__push_files, mcp__jira__update_issue
---

# SDLC Stage 4 · Commit & Pull Request

You are running Stage 4 of the SDLC automation pipeline.

## Pre-check
Read `.claude/sdlc-state.json`. Stage must be `"build"`.
Confirm `test_count > 0` and `coverage_pct >= 80`. If not, tell the user to run `/sdlc-build` first.

## Your Tasks

### 1. Stage and commit
```bash
git add -A
git status   # show what's being committed
```

Write a Conventional Commit message:
- `feat(scope): <what was added>` for new features
- `fix(scope): <what was fixed>` for bug fixes
- `test(scope): add tests for <feature>` if test-only

Format:
```
feat(PROJ-42): add user login with JWT auth

- Implements POST /auth/login endpoint
- Returns signed JWT valid for 24h
- Full test coverage (87%)

Refs: PROJ-42
```

```bash
git commit -m "<message>"
git push origin <branch-name>
```

### 2. Open Pull Request
Call `mcp__github__create_pull_request` with:

**Title:** `[PROJ-42] <Jira card summary>`

**Body template:**
```markdown
## Summary
<1-2 sentence description from Jira card>

## Jira Card
[PROJ-42](<jira-card-url>)

## Changes
- <bullet list of what changed>

## Test Coverage
- Tests added: <count>
- Coverage: <pct>%
- All tests passing ✅

## Definition of Done
- [ ] All acceptance criteria met
- [ ] Tests written first (TDD)
- [ ] Coverage ≥ 80%
- [ ] No linting errors
- [ ] MR description complete

## How to Test
<step-by-step instructions to verify the feature>
```

### 3. Update Jira
Move card to `In Review`. Post comment with the MR URL.

### 4. Update state
```json
{
  "stage": "commit",
  "pr_url": "https://github.com/org/repo/pull/99",
  "pr_number": 99,
  "commit_sha": "<sha>"
}
```

## Done Condition
Print:
```
✅ Stage 4 complete. MR opened: <pr_url>
Run /sdlc-review to start the agent code review.
```
