---
description: SDLC Stage 5.4 — Analyze failed tests and generate healing suggestions using Anthropic API. Proposes selector fixes, timing adjustments, and code improvements. Invoke with /sdlc-test-heal.
allowed-tools: Read, Write, Bash
---

# SDLC Stage 5.4 · Test Healing & Auto-Remediation

You are running Stage 5.4 of the SDLC automation pipeline - Test Healing.

## Input
Reads from:
- `runs/<run-id>/test_execution.json` - test execution results from Stage 5.3
- `runs/<run-id>/playwright_tests/` - original test scripts
- Error logs, screenshots, and stack traces from failed tests

## Your Tasks

### 1. Analyze test failures
For each failed test:
- Read the error message and stack trace
- Examine the screenshot at failure point
- Review the test script that failed
- Identify failure category:
  - Selector issues (element not found, stale reference)
  - Timing issues (race conditions, slow loading)
  - Assertion failures (expected vs actual mismatch)
  - Environmental issues (API down, data setup)
  - Flaky tests (intermittent failures)

### 2. Generate healing suggestions using Anthropic API
- Use Anthropic API (Claude) with vision capabilities to analyze failure screenshots
- For each failed test, generate:
  - Root cause analysis
  - Specific fix recommendations
  - Updated test code with fixes applied
  - Alternative selector strategies
  - Improved wait conditions
  - Enhanced assertions

### 3. Propose auto-remediation
For each failure, provide:
- **Automated Fix**: Updated test script that should resolve the issue
- **Confidence Score**: How confident the LLM is the fix will work (0-100%)
- **Validation Steps**: Manual checks to verify the fix
- **Alternative Approaches**: Other ways to handle the scenario

### 4. Save healing report
Write to `runs/<run-id>/test_healing.json`:
```json
{
  "run_id": "<run-id>",
  "analyzed_at": "<ISO timestamp>",
  "failures_analyzed": 0,
  "auto_fixable": 0,
  "manual_review_needed": 0,
  "healing_suggestions": [
    {
      "test_id": "story-001.spec.ts::AC1",
      "failure_category": "selector_issue",
      "root_cause": "Button selector changed from #submit to .btn-submit",
      "confidence_score": 95,
      "automated_fix": {
        "file_path": "story-001.spec.ts",
        "original_code": "await page.click('#submit')",
        "fixed_code": "await page.click('button[type=\"submit\"]')",
        "explanation": "Use semantic selector instead of ID"
      },
      "validation_steps": [
        "Verify button still has type='submit' attribute",
        "Re-run test to confirm fix"
      ],
      "alternatives": [
        "Use data-testid attribute",
        "Use role-based selector: getByRole('button', { name: 'Submit' })"
      ]
    }
  ]
}
```

### 5. Apply auto-fixes (optional)
- Present healing suggestions to user
- Ask for approval to apply automated fixes
- If approved, update test scripts with fixes
- Re-run failed tests to validate fixes
- Track fix success rate

## LLM Integration
- Uses Anthropic API with vision (claude-sonnet-4-6)
- Analyzes failure screenshots to understand UI state
- Temperature: 0.3 (balanced between creativity and consistency)
- System prompt: QA debugging expert persona

## Done Condition
Print summary:
```
✅ Stage 5.4 complete. Analyzed <N> failures:
   Auto-fixable: <M> (confidence >= 80%)
   Manual review: <X>
   
   Healing report: runs/<run-id>/test_healing.json
```

Prompt user:
```
Apply automated fixes? (Y/n)
If yes: Update test scripts and re-run Stage 5.3
If no: Review healing suggestions manually
```
