---
description: SDLC Stage 6 — Read review comments and failing tests, apply targeted fixes, commit, push, and loop autonomously until all CI checks and tests are green. Invoke with /sdlc-fix.
allowed-tools: Read, Write, Edit, Bash, mcp__github__get_pull_request_reviews, mcp__github__list_pull_request_comments, mcp__github__get_check_runs, mcp__github__push_files
---

# SDLC Stage 6 · Autonomous Fix Loop

You are running Stage 6 of the SDLC automation pipeline.
This stage loops until ALL of the following are true:
1. All tests pass locally
2. All CI checks pass on GitHub
3. No unresolved `REQUEST_CHANGES` review comments

## Pre-check
Read `.claude/sdlc-state.json`. Stage must be `"review"`.
If `review_result === "APPROVE"` and `ci_passing === true`, tell user MR is already green — nothing to fix.

## Fix Loop (repeat until exit condition met)

### Iteration start — diagnose

**A. Collect review comments**
Call `mcp__github__get_pull_request_reviews` and `mcp__github__list_pull_request_comments`.
List all unresolved `REQUEST_CHANGES` comments grouped by file.

**B. Collect failing tests**
```bash
npm test 2>&1 | tail -60   # capture test output
```
List failing test names and error messages.

**C. Collect CI failures**
Call `mcp__github__get_check_runs`. List failing checks and their log summaries.

**D. Triage**
Deduplicate root causes. One root cause may explain multiple failures.
Priority order: test failures → CI failures → review comments.

---

### Apply fixes

For each root cause (most impactful first):

1. Read the relevant source file(s)
2. Apply the minimal targeted fix — do not refactor unrelated code
3. If a test was wrong (testing implementation not behaviour), fix the test too
4. Run only the affected tests to verify the fix works in isolation:
   ```bash
   npm test -- --testPathPattern=<filename>
   ```

---

### Verify all tests pass
```bash
npm test
```
If any failures remain, go back to **Diagnose**.

---

### Commit and push
```bash
git add -A
git commit -m "fix(PROJ-XX): <concise description of what was fixed>"
git push origin <branch>
```

---

### Check CI
Wait up to 3 minutes, polling every 30 seconds:
```bash
sleep 30 && <check CI status via mcp__github__get_check_runs>
```
If CI still failing after push, read the new logs and loop back to **Diagnose**.

---

### Re-run review check
Call `mcp__github__get_pull_request_reviews` to see if all comments are now resolved.
If `REQUEST_CHANGES` still present, treat remaining comments as new diagnose input.

---

## Exit condition
All three conditions met:
- ✅ Local tests: 100% passing
- ✅ CI checks: all green
- ✅ Reviews: no unresolved `REQUEST_CHANGES`

Update state:
```json
{
  "stage": "fix",
  "iterations": <number>,
  "final_status": "production-ready"
}
```

Print:
```
✅ Stage 6 complete after <N> iteration(s).
🚀 MR is production-ready. All checks green. Safe to merge.
```

## Safety guardrail
If after **5 iterations** the loop has not exited, stop and print:
```
⚠️  Stopped after 5 iterations. Remaining issues require human review.
Open issues:
<list remaining failures>
```
This prevents infinite loops on issues that require architectural decisions.
