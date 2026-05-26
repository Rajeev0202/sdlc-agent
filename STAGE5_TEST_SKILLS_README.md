# Stage 5 Test Management Skills - Setup Guide

This document explains how to configure and use the new Stage 5 Test Management skills that leverage **Playwright** automation and **Anthropic Claude API** for intelligent test generation.

## Overview

Stage 5 now includes 4 automated skills:

1. **`/sdlc-test-manual`** - Generate detailed manual test cases using Claude AI
2. **`/sdlc-test-automation`** - Generate Playwright TypeScript automation scripts using Claude AI
3. **`/sdlc-test-execute`** - Execute Playwright tests and collect results
4. **`/sdlc-test-heal`** - Analyze test failures and suggest fixes using Claude AI with vision

## Prerequisites

### 1. Anthropic API Key (Required)

The test skills use **Claude Sonnet 4.6** to generate intelligent test cases and automation scripts.

**Get your API key:**
1. Visit [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

**Configure the key:**

Edit your `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

**Cost estimate:**
- Manual test generation: ~500-1000 tokens per story
- Automation script generation: ~2000-3000 tokens per story
- Test healing: ~1000-2000 tokens per failure
- Claude Sonnet 4.6 pricing: Check [Anthropic Pricing](https://www.anthropic.com/pricing)

### 2. Python Dependencies

Install required packages:

```bash
pip install anthropic openpyxl
```

- **anthropic** - Official Anthropic Python SDK for Claude API
- **openpyxl** - For generating Excel test case files

### 3. Playwright (Optional - for test execution)

To actually execute generated tests:

```bash
# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install
```

**Note:** If Playwright is not installed, Stage 5.3 (Execute Tests) will run in **simulation mode** for demo purposes.

## Usage

### Via UI (Recommended)

1. **Stage 1**: Ingest requirements from Confluence
2. **Stage 2**: Generate user stories
3. **Stage 5 - Test Management Workflow**:
   - Click **"Generate Manual Tests"** → Runs `/sdlc-test-manual`
   - Click **"Generate Automation"** → Runs `/sdlc-test-automation`
   - Click **"Execute Tests"** → Runs `/sdlc-test-execute`
   - Click **"Heal Tests"** (if failures) → Runs `/sdlc-test-heal`

### Via Claude Code CLI

```bash
# Generate manual test cases
/sdlc-test-manual

# Generate Playwright automation scripts
/sdlc-test-automation

# Execute tests
/sdlc-test-execute

# Analyze and heal failures
/sdlc-test-heal
```

## Output Files

All outputs are organized under `runs/<run-id>/`:

```
runs/run-20260525-123456-abc123/
├── manual_test_cases.json      # JSON with all test cases
├── manual_test_cases.xlsx      # Excel file for QA team
├── playwright_tests/           # Directory with .spec.ts files
│   ├── story-001.spec.ts
│   ├── story-002.spec.ts
│   └── ...
├── automation_scripts.json     # Metadata about generated scripts
├── test_execution.json         # Test results
├── test-report.html           # HTML test report
└── test_healing.json          # Healing suggestions for failures
```

## Skill Details

### 5.1 - Manual Test Generation (`/sdlc-test-manual`)

**What it does:**
- Reads approved user stories from `.claude/sdlc-state.json`
- For each story and acceptance criterion, Claude generates:
  - Detailed test steps (numbered, actionable)
  - Test data specifications
  - Expected results
  - Priority (High/Medium/Low)
  - Type (Functional/UI/API/Performance/Security)
- Outputs JSON and Excel files

**LLM Configuration:**
- Model: `claude-sonnet-4-6`
- Temperature: 0.3 (deterministic)
- Persona: QA engineer with testing best practices

### 5.2 - Automation Script Generation (`/sdlc-test-automation`)

**What it does:**
- Reads approved user stories
- For each story, Claude generates complete Playwright TypeScript test files:
  - Proper imports and setup
  - Intelligent selectors (data-testid, role-based, CSS)
  - Appropriate waits and assertions
  - Error handling and edge cases
- Outputs `.spec.ts` files ready to run

**LLM Configuration:**
- Model: `claude-sonnet-4-6`
- Temperature: 0.2 (more deterministic for code)
- Persona: Test automation engineer with Playwright expertise

### 5.3 - Test Execution (`/sdlc-test-execute`)

**What it does:**
- Executes all generated Playwright tests
- Collects results: passed, failed, skipped, execution time
- Generates HTML report with visual dashboard
- Captures screenshots and videos for failures (when Playwright installed)

**Execution modes:**
- **Real mode**: Runs actual Playwright tests (requires npm/npx)
- **Simulation mode**: Generates sample results for demo (fallback)

### 5.4 - Test Healing (`/sdlc-test-heal`)

**What it does:**
- Analyzes failed test results
- For each failure, Claude:
  - Categorizes failure (selector issue, timing, assertion, environmental)
  - Analyzes error messages and screenshots
  - Suggests specific fixes with confidence scores
  - Provides alternative approaches
- Outputs healing report with auto-fixable suggestions (>80% confidence)

**LLM Configuration:**
- Model: `claude-sonnet-4-6` (with vision for screenshot analysis)
- Temperature: 0.3
- Persona: QA debugging expert

## Fallback Modes

If Anthropic API key is not configured:

- Uses **MockClaudeClient** which generates deterministic placeholder data
- Allows UI/skill testing without incurring API costs
- Can also use **Google Gemini** if `GOOGLE_API_KEY` is set
- Can use **Copilot Bridge** if available (VS Code extension)

Check console output to see which backend is active:
```
[WARNING] Using MockClaudeClient. Set ANTHROPIC_API_KEY for real LLM integration.
```

## Troubleshooting

### "anthropic package not installed"
```bash
pip install anthropic
```

### "No approved stories found"
- Ensure Stage 1 (Ingest) and Stage 2 (Stories) completed successfully
- Check `.claude/sdlc-state.json` exists and has `stories` array

### "Playwright not found"
- Stage 5.3 will run in simulation mode (no actual test execution)
- To enable real execution: `npm install -D @playwright/test && npx playwright install`

### API Rate Limits
- Anthropic API has rate limits based on your plan
- If you hit limits, wait a few minutes or upgrade your plan
- Check [Anthropic Dashboard](https://console.anthropic.com/) for usage

## Integration with Playwright MCP Server (Future)

For advanced test execution with real-time streaming and better error handling, you can integrate the **Playwright MCP Server**:

1. Install Playwright MCP server: `npm install -g @playwright/mcp-server`
2. Configure in `~/.claude.json`:
```json
{
  "mcpServers": {
    "playwright": {
      "type": "url",
      "url": "http://localhost:8080/mcp/sse"
    }
  }
}
```
3. Update `test_execute_skill.py` to use MCP tools instead of subprocess

## Cost Optimization Tips

1. **Use caching**: Anthropic API supports prompt caching - similar stories reuse cached context
2. **Batch processing**: Generate tests for all stories in one run instead of individually
3. **Fallback to mock**: For development/testing, use mock client without API key
4. **Gemini alternative**: Use `GOOGLE_API_KEY` instead if you have Gemini access

## Next Steps

After configuring your API key:

1. **Test the skills**: Run through Stage 1 → Stage 2 → Stage 5 workflow
2. **Review outputs**: Check `runs/<run-id>/` for generated files
3. **Customize prompts**: Edit skill files in `sdlc_agent/skills/` to tune LLM behavior
4. **Add real Playwright**: Install Playwright to enable actual test execution

## Support

For issues or questions:
- Check logs in console output
- Review `runs/<run-id>/` for detailed outputs
- See skill definitions in `.claude/skills/sdlc-test-*/SKILL.md`
- Submit issues to project repository
