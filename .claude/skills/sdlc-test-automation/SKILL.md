---
description: SDLC Stage 5.2 — Generate Playwright automation scripts from user stories using Anthropic API. Creates TypeScript test files with intelligent selectors and assertions. Invoke with /sdlc-test-automation.
allowed-tools: Read, Write, Bash
---

# SDLC Stage 5.2 · Test Automation Script Generation

You are running Stage 5.2 of the SDLC automation pipeline - Playwright Automation Script Generation.

## Input
Reads from:
- `.claude/sdlc-state.json` - approved user stories
- `runs/<run-id>/manual_test_cases.json` - manual test cases from Stage 5.1

## Your Tasks

### 1. Load stories and manual tests
- Read approved user stories from state file
- Read manual test cases to understand test scenarios
- Identify which test cases can be automated (UI flows)

### 2. Generate Playwright scripts using Anthropic API
For each automatable test scenario:
- Use Anthropic API (Claude) to generate intelligent Playwright TypeScript code
- Each script should include:
  - Proper imports (test, expect from @playwright/test)
  - Intelligent selectors (data-testid, role-based, CSS)
  - Appropriate waits (waitForSelector, waitForLoadState)
  - Clear assertions covering acceptance criteria
  - Error handling and edge cases
  - Page Object Model patterns where applicable

### 3. Validate generated scripts
- Ensure scripts follow Playwright best practices
- Check for proper async/await usage
- Verify all acceptance criteria are covered
- Validate selector strategies are robust

### 4. Save automation scripts
Write to `runs/<run-id>/playwright_tests/`:
```
runs/<run-id>/playwright_tests/
├── story-001.spec.ts
├── story-002.spec.ts
└── test-config.json
```

Each test file structure:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Story US-001: <Title>', () => {
  test('AC1: <Acceptance Criterion>', async ({ page }) => {
    // Test implementation
  });
});
```

Also save metadata in `runs/<run-id>/automation_scripts.json`:
```json
{
  "run_id": "<run-id>",
  "generated_at": "<ISO timestamp>",
  "total_scripts": 0,
  "scripts": [
    {
      "story_id": "US-001",
      "file_path": "story-001.spec.ts",
      "test_count": 3,
      "selectors_used": ["data-testid", "role"],
      "coverage": ["AC1", "AC2", "AC3"]
    }
  ]
}
```

## LLM Integration
- Uses Anthropic API with user-provided API key
- Model: claude-sonnet-4-6 (latest Sonnet)
- Temperature: 0.2 (more deterministic for code generation)
- System prompt: Test automation engineer persona with Playwright expertise

## Done Condition
Print summary:
```
✅ Stage 5.2 complete. Generated <N> Playwright test scripts for <M> stories.
   Output: runs/<run-id>/playwright_tests/
           runs/<run-id>/automation_scripts.json
```
