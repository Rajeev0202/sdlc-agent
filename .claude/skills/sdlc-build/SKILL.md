---
description: SDLC Stage 3 — Pull a Jira card, create a feature branch, and implement it using strict TDD (Red → Green → Refactor). Invoke with /sdlc-build <JIRA-CARD-ID>.
allowed-tools: Read, Write, Edit, Bash, mcp__jira__get_issue, mcp__jira__update_issue, mcp__github__create_branch
---

# SDLC Stage 3 · TDD Implementation

You are running Stage 3 of the SDLC automation pipeline.

## Pre-check
Read `.claude/sdlc-state.json`. Stage must be `"plan"` or `"build"`.

## Input
Arguments: $ARGUMENTS (expected: Jira card ID, e.g. `PROJ-42`)

## Your Tasks

### 1. Fetch the Jira card
Call `mcp__jira__get_issue` with the card ID. Extract:
- Acceptance criteria / Given-When-Then scenarios
- Definition of Done
- Any linked sub-tasks

### 2. Create a feature branch
Branch name format: `feature/<card-id>-<slugified-summary>`
```bash
git checkout -b feature/PROJ-42-user-login
```
Or use `mcp__github__create_branch` if the repo is remote-first.

### 3. TDD Cycle — STRICTLY in this order

#### 🔴 RED — Write failing tests first
- Read the acceptance criteria
- Write test file(s) covering every Given/When/Then scenario
- Tests MUST fail at this point (assert on code that doesn't exist yet)
- Run the test suite and confirm failures:
  ```bash
  npm test        # or pytest / go test / etc — detect from project
  ```
- Do NOT write implementation code yet

#### 🟢 GREEN — Minimal implementation
- Write the minimum code needed to make every test pass
- No gold-plating, no extra features
- Run tests and confirm all pass

#### 🔵 REFACTOR — Clean up
- Remove duplication
- Apply SOLID principles, project conventions from CLAUDE.md
- Run tests again to confirm they still pass after refactor

### 4. Check coverage
```bash
# detect and run coverage tool
npm test -- --coverage   # or pytest --cov / go test -cover
```
If coverage < 80%, write additional tests before proceeding.

### 5. Update Jira
Move the card to `In Review` and add a comment with:
- Branch name
- Summary of what was implemented
- Test count and coverage %

### 6. Update state
```json
{
  "stage": "build",
  "current_card": "PROJ-42",
  "branch": "feature/PROJ-42-user-login",
  "test_count": 12,
  "coverage_pct": 87
}
```

## Done Condition
All tests green, coverage ≥ 80%. Print:
```
✅ Stage 3 complete. Run /sdlc-commit to push and open MR.
```
