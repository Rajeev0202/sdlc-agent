---
description: SDLC Stage 5 — Review the open Pull Request diff for bugs, code smells, and coverage gaps. Run the test suite. Post inline review comments on GitHub. Invoke with /sdlc-review.
allowed-tools: Read, Write, Bash, mcp__github__get_pull_request, mcp__github__list_pull_request_files, mcp__github__create_review, mcp__github__get_check_runs
---

# SDLC Stage 5 · Agent Code Review

You are running Stage 5 of the SDLC automation pipeline.

## Pre-check
Read `.claude/sdlc-state.json`. Stage must be `"commit"`. Load `pr_number`.

## Your Tasks

### 1. Fetch the diff
Call `mcp__github__get_pull_request` and `mcp__github__list_pull_request_files`
to get the full changed file list and diffs.

### 2. Run tests locally
```bash
npm test         # detect test runner from project (jest / pytest / go test)
```
Capture stdout/stderr. Note any failures.

### 3. Check CI status
Call `mcp__github__get_check_runs` for the PR's head SHA.
List all check runs and their conclusions.

### 4. Review the diff against this checklist

For each changed file, evaluate:

**Correctness**
- [ ] Does the implementation match the acceptance criteria?
- [ ] Are edge cases handled (null, empty, boundary values)?
- [ ] Are errors caught and handled gracefully?

**Test Quality**
- [ ] Tests written BEFORE implementation (TDD evidence)?
- [ ] Are all Given/When/Then scenarios covered?
- [ ] Do tests assert on behaviour, not implementation details?
- [ ] Are mocks/stubs used appropriately?

**Code Quality**
- [ ] No obvious code smells (long methods, deep nesting, magic numbers)?
- [ ] No duplicated logic that should be extracted?
- [ ] Naming is clear and consistent with existing codebase conventions?
- [ ] No commented-out code or debug statements?

**Security**
- [ ] No secrets or credentials hardcoded?
- [ ] User input is validated/sanitised?
- [ ] Auth/permissions checked where needed?

**Performance**
- [ ] No N+1 query patterns?
- [ ] No blocking I/O in hot paths?

### 5. Post review on GitHub
Call `mcp__github__create_review` with:
- **event:** `REQUEST_CHANGES` if any issue found, `APPROVE` if all clear
- **body:** Executive summary of findings
- **comments:** Inline comments for each specific issue with file path, line number, and suggested fix

Format each comment as:
```
🔴 [Bug] / 🟡 [Warning] / 🔵 [Suggestion]
<Explanation>
<Suggested fix or example>
```

### 6. Update state
```json
{
  "stage": "review",
  "review_result": "REQUEST_CHANGES" | "APPROVE",
  "issues_count": 3,
  "ci_passing": true | false,
  "tests_passing": true | false
}
```

## Done Condition
If `review_result === "APPROVE"` AND `ci_passing` AND `tests_passing`:
```
✅ Stage 5 complete. MR is production-ready! Merge when ready.
```

If issues found:
```
⚠️  Stage 5 complete. Review posted with <N> issues.
Run /sdlc-fix to resolve them automatically.
```
