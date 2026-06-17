---
description: SDLC Stage 5.3 — Execute Playwright tests via MCP server and collect results. Runs automated tests and generates detailed execution reports. Invoke with /sdlc-test-execute.
allowed-tools: Read, Write, Bash, mcp__playwright__run_tests, mcp__playwright__get_report
---

# SDLC Stage 5.3 · Test Execution

You are running Stage 5.3 of the SDLC automation pipeline - Playwright Test Execution.

## Input
Reads from:
- `runs/<run-id>/playwright_tests/` - generated Playwright scripts from Stage 5.2
- `runs/<run-id>/automation_scripts.json` - test metadata

## Your Tasks

### 1. Prepare test environment
- Verify Playwright MCP server is available
- Check test scripts are present and valid TypeScript
- Set up test configuration (browsers, viewport, baseURL)

### 2. Execute tests via Playwright MCP server
- Use `mcp__playwright__run_tests` tool to execute all test scripts
- Run tests in parallel where possible
- Collect real-time execution logs
- Capture screenshots for failures
- Record videos for failed test scenarios

### 3. Process test results
- Parse Playwright JSON reporter output
- Categorize results: passed, failed, skipped, flaky
- Extract failure details: error messages, stack traces, screenshots
- Calculate pass rate and execution time

### 4. Save execution results
Write to `runs/<run-id>/test_execution.json`:
```json
{
  "run_id": "<run-id>",
  "executed_at": "<ISO timestamp>",
  "total_tests": 0,
  "passed": 0,
  "failed": 0,
  "skipped": 0,
  "flaky": 0,
  "pass_rate": 0.0,
  "execution_time_ms": 0,
  "results": [
    {
      "test_id": "story-001.spec.ts::AC1",
      "story_id": "US-001",
      "status": "passed|failed|skipped",
      "duration_ms": 0,
      "error": null,
      "screenshot_path": null,
      "video_path": null
    }
  ]
}
```

Also generate HTML report at `runs/<run-id>/test-report.html` with:
- Visual test results dashboard
- Failed test screenshots
- Execution timeline
- Coverage matrix

## Playwright MCP Integration
- Uses Playwright MCP server for test execution
- Supports Chrome, Firefox, Safari browsers
- Runs in headless mode by default
- Captures artifacts (screenshots, videos, traces)

## Done Condition
Print summary:
```
✅ Stage 5.3 complete. Executed <N> tests with <X>% pass rate.
   Passed: <passed> | Failed: <failed> | Skipped: <skipped>
   Report: runs/<run-id>/test-report.html
   Results: runs/<run-id>/test_execution.json
```

If failures detected, prompt:
```
❌ <N> tests failed. Run /sdlc-test-heal to analyze and fix failures.
```
