# Stage 5 Test Skills - Quick Start Guide

## ✅ What's Been Integrated

I've created **4 new test skills** for Stage 5 that use **Playwright** automation and **Anthropic Claude API** for intelligent test generation:

1. **`/sdlc-test-manual`** - Generate detailed manual test cases
2. **`/sdlc-test-automation`** - Generate Playwright automation scripts  
3. **`/sdlc-test-execute`** - Execute Playwright tests
4. **`/sdlc-test-heal`** - Analyze failures and suggest fixes

All skills are now integrated with the web UI and ready to use!

## 🚀 Try It Now (3 Steps)

### Step 1: Configure Anthropic API Key (Optional)

For **real LLM-powered test generation**, add your Anthropic API key:

1. Get your key from: **https://console.anthropic.com/**
2. Edit [.env](.env) file:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
   ```
3. Restart the server (or skip for demo mode)

**Note:** Without an API key, skills work in **mock mode** with deterministic sample data.

### Step 2: Install Dependencies

```bash
# Core dependencies
pip install -r requirements-stage5.txt

# Optional: Install Playwright for real test execution
npm install -D @playwright/test
npx playwright install
```

### Step 3: Test the Workflow

The server is already running at: **http://127.0.0.1:5002**

1. **Open in browser**: http://127.0.0.1:5002
2. **Stage 1**: Enter a Confluence URL or local file → Click "Ingest Requirements"
3. **Stage 2**: Click "Generate Stories"  
4. **Stage 5 - Test Management**:
   - Click **"Generate Manual Tests"** → Creates JSON + Excel with test cases
   - Click **"Generate Automation"** → Creates Playwright .spec.ts files
   - Click **"Execute Tests"** → Runs tests (or simulates if Playwright not installed)
   - Click **"Heal Tests"** → Analyzes failures and suggests fixes

## 📂 Check Your Outputs

After running Stage 5, find all outputs in:

```
runs/run-<timestamp>-<id>/
├── manual_test_cases.json      # All test cases (JSON)
├── manual_test_cases.xlsx      # QA-friendly Excel file
├── automation_scripts.json     # Metadata about scripts
├── playwright_tests/           # Generated .spec.ts files
│   ├── story-001.spec.ts
│   └── story-002.spec.ts
├── test_execution.json         # Test results
├── test-report.html           # Visual HTML report
└── test_healing.json          # Healing suggestions
```

## 🎯 What Each Skill Does

### 1. Generate Manual Tests (`/sdlc-test-manual`)
- **Input**: User stories from Stage 2
- **Process**: Claude generates detailed test cases for each acceptance criterion
- **Output**: JSON + Excel with test steps, data, expected results, priority
- **LLM Model**: Claude Sonnet 4.6 (temperature 0.3)

### 2. Generate Automation (`/sdlc-test-automation`)
- **Input**: User stories from Stage 2
- **Process**: Claude writes complete Playwright TypeScript test files
- **Output**: `.spec.ts` files ready to run with `npx playwright test`
- **LLM Model**: Claude Sonnet 4.6 (temperature 0.2 for code)

### 3. Execute Tests (`/sdlc-test-execute`)
- **Input**: Generated Playwright scripts from step 2
- **Process**: Runs tests via npm/npx (or simulates if not installed)
- **Output**: JSON results + HTML report with pass/fail stats
- **Real Execution**: Requires `npm install -D @playwright/test`

### 4. Heal Tests (`/sdlc-test-heal`)
- **Input**: Failed tests from step 3
- **Process**: Claude analyzes failures and suggests specific fixes
- **Output**: Healing report with confidence scores and code fixes
- **LLM Model**: Claude Sonnet 4.6 with vision (for screenshot analysis)

## 🔧 Current Status

✅ **Server Running**: http://127.0.0.1:5002 (PID: 13824)  
✅ **Skills Registered**: All 4 skills available in Claude Code CLI  
✅ **UI Integration**: All 4 buttons connected to skill automations  
✅ **LLM Backend**: Currently using **stub** mode (no API key configured)

To switch to **real Claude API**:
```bash
# Edit .env
ANTHROPIC_API_KEY=sk-ant-api03-your-key

# Restart server
# (Kill old: taskkill /PID 13824 /F)
python -m sdlc_agent.web.app
```

## 📚 Full Documentation

- **Setup Guide**: [STAGE5_TEST_SKILLS_README.md](STAGE5_TEST_SKILLS_README.md) - Complete setup instructions
- **Integration Summary**: [STAGE5_INTEGRATION_SUMMARY.md](STAGE5_INTEGRATION_SUMMARY.md) - Technical details
- **Dependencies**: [requirements-stage5.txt](requirements-stage5.txt) - Python packages needed

## 🎓 Example Workflow

**Scenario**: You have a BRD document at `samples/brd_natwest_card_freeze.md`

1. **UI → Stage 1**: 
   - Input: `samples/brd_natwest_card_freeze.md`
   - Output: Structured requirements with user stories

2. **UI → Stage 2**: 
   - Generates user stories with acceptance criteria
   - Saves to `.claude/sdlc-state.json`

3. **UI → Stage 5.1** (Manual Tests):
   - Reads stories from state file
   - Claude generates 1-3 test cases per acceptance criterion
   - Output: `runs/<id>/manual_test_cases.xlsx`

4. **UI → Stage 5.2** (Automation):
   - Reads stories from state file
   - Claude writes Playwright test files
   - Output: `runs/<id>/playwright_tests/story-*.spec.ts`

5. **UI → Stage 5.3** (Execute):
   - Runs all Playwright tests
   - Output: HTML report with results

6. **UI → Stage 5.4** (Heal - if failures):
   - Analyzes each failure
   - Suggests specific fixes with confidence scores
   - Output: `runs/<id>/test_healing.json`

## 💡 Tips

1. **Mock Mode is Fine**: Skills work without API key for testing/demo
2. **Excel for QA**: Manual test cases export to Excel for human review
3. **Playwright Optional**: Test execution simulates if Playwright not installed
4. **Cost Optimization**: ~500-3000 tokens per story (check Anthropic pricing)
5. **Customize Prompts**: Edit files in `.claude/skills/sdlc-test-*/` to tune behavior

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| "No approved stories found" | Run Stage 1 and 2 first |
| "anthropic not installed" | `pip install anthropic` |
| "Playwright not found" | Optional - runs in simulation mode |
| Mock client active | Set `ANTHROPIC_API_KEY` for real LLM |

## 🎉 You're Ready!

**Next Action**: Open http://127.0.0.1:5002 and try the Stage 5 workflow!

If you have questions, check:
- Console logs for detailed execution info
- `runs/<run-id>/` for all generated files
- Skill definitions in `.claude/skills/sdlc-test-*/SKILL.md`

---

**Integration Complete**: 2026-05-25  
**Skills Created**: 4 (manual, automation, execute, heal)  
**LLM Integration**: Anthropic Claude Sonnet 4.6  
**Automation Tool**: Playwright (TypeScript)
