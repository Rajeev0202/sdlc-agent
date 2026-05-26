---
description: SDLC Stage 5.1 — Generate detailed manual test cases from user stories using Anthropic API. Creates comprehensive test scenarios with steps, data, and expected results. Invoke with /sdlc-test-manual.
allowed-tools: Read, Write, Bash
---

# SDLC Stage 5.1 · Manual Test Case Generation

You are running Stage 5.1 of the SDLC automation pipeline - Manual Test Case Generation.

## Input
Reads from `.claude/sdlc-state.json` containing approved user stories and acceptance criteria from Stage 2.

## Your Tasks

### 1. Load approved stories
- Read `.claude/sdlc-state.json` to get the approved user stories
- Each story contains: id, persona, want, so_that, acceptance_criteria

### 2. Generate detailed test cases using Anthropic API
For each user story and acceptance criterion:
- Use Anthropic API (Claude) to generate comprehensive manual test cases
- Each test case should include:
  - Unique TC ID (TC-001, TC-002, etc.)
  - Clear title describing what's being tested
  - Detailed test steps (numbered, actionable)
  - Test data specifications
  - Expected results
  - Priority (High/Medium/Low)
  - Type (Functional/UI/API/Performance/Security)

### 3. Validate test coverage
- Ensure every acceptance criterion has at least one test case
- Check for edge cases and negative scenarios
- Verify test cases are specific and executable

### 4. Save test cases
Write to `runs/<run-id>/manual_test_cases.json`:
```json
{
  "run_id": "<run-id>",
  "generated_at": "<ISO timestamp>",
  "total_test_cases": 0,
  "test_cases": [
    {
      "tc_id": "TC-001",
      "story_id": "US-001",
      "title": "Test case title",
      "steps": ["1. Action", "2. Action"],
      "test_data": "Specific inputs",
      "expected_result": "Expected outcome",
      "priority": "High",
      "type": "Functional"
    }
  ]
}
```

Also generate Excel file at `runs/<run-id>/manual_test_cases.xlsx` for QA team review.

## LLM Integration
- Uses Anthropic API with user-provided API key
- Model: claude-sonnet-4-6 (latest Sonnet)
- Temperature: 0.3 (deterministic test generation)
- System prompt: QA engineer persona with testing best practices

## Done Condition
Print summary:
```
✅ Stage 5.1 complete. Generated <N> manual test cases across <M> stories.
   Output: runs/<run-id>/manual_test_cases.json
           runs/<run-id>/manual_test_cases.xlsx
```
