# Stage 5 Redesign - 4-Button Test Workflow

## ✅ Completed

### 1. Folder Structure
- ✅ Created `Manual_Test_Cases/` folder
- ✅ Created `Automation_Scripts/` folder
- ✅ Created `Results/` folder

### 2. Frontend UI
- ✅ Updated Stage 5 HTML with 4 workflow buttons:
  - Button 1: Generate Manual Test Cases (clipboard icon)
  - Button 2: Generate Automation Scripts (robot icon)
  - Button 3: Execute Tests (play icon)
  - Button 4: Heal Failed Tests (magic icon - orange gradient)
- ✅ Added CSS styling for workflow steps
- ✅ Added special `healing` button style (orange/red gradient)
- ✅ Responsive design for mobile

## 🔄 Next Steps Required

### 3. Backend API Endpoints (Flask)

Need to add to `sdlc_agent/web/app.py`:

```python
@app.post("/api/stage5/manual-tests")
def api_stage5_manual():
    """Generate manual test cases Excel"""
    # 1. Read backlog from runs/
    # 2. Generate Excel using write_manual_tests_xlsx()
    # 3. Save to Manual_Test_Cases/ folder
    # 4. Return file path and summary
    pass

@app.post("/api/stage5/automation-scripts")
def api_stage5_automation():
    """Generate Playwright automation scripts from manual tests"""
    # 1. Read manual test cases Excel
    # 2. Generate Playwright TypeScript scripts
    # 3. Save to Automation_Scripts/ folder
    # 4. Return script paths and count
    pass

@app.post("/api/stage5/execute-tests")
def api_stage5_execute():
    """Execute Playwright automation scripts"""
    # 1. Run npx playwright test in Automation_Scripts/
    # 2. Capture output and results
    # 3. Save results to Results/ folder
    # 4. Return execution summary with pass/fail counts
    pass

@app.post("/api/stage5/heal-tests")
def api_stage5_heal():
    """Analyze failures and fix scripts using Claude"""
    # 1. Read test failures from Results/
    # 2. Analyze failure patterns
    # 3. Use Claude to generate fixes
    # 4. Update scripts in Automation_Scripts/
    # 5. Re-run tests automatically
    # 6. Return healing summary
    pass
```

### 4. Frontend JavaScript (app.js)

Need to add handlers:

```javascript
async function stage5Manual() {
  // Call /api/stage5/manual-tests
  // Display Excel file link
  // Enable automation button
}

async function stage5Automation() {
  // Call /api/stage5/automation-scripts
  // Display generated script count
  // Enable execute button
}

async function stage5Execute() {
  // Call /api/stage5/execute-tests
  // Display test results
  // If failures, enable heal button
}

async function stage5Heal() {
  // Call /api/stage5/heal-tests
  // Display healing progress
  // Show fixed tests
}

// Add to handlers object:
const handlers = {
  ...existing,
  'stage5-manual': stage5Manual,
  'stage5-automation': stage5Automation,
  'stage5-execute': stage5Execute,
  'stage5-heal': stage5Heal
};
```

### 5. Test Healing Logic

Intelligent healing strategy:
1. Parse Playwright JSON report
2. Identify failure patterns:
   - Selector not found → Suggest updated selectors
   - Timeout → Increase waits or fix async issues
   - Assertion failed → Check expected vs actual
3. Use Claude to analyze and generate fixes
4. Apply fixes to scripts
5. Re-run failed tests only

### 6. Workflow State Management

```javascript
const stage5State = {
  manualTestsGenerated: false,
  automationScriptsGenerated: false,
  testsExecuted: false,
  hasFailures: false
};

// Enable buttons based on state:
// - Manual: Always enabled after Stage 4
// - Automation: Enabled after manual tests
// - Execute: Enabled after automation scripts
// - Heal: Enabled only if execute has failures
```

## 📁 Folder Structure

```
sdlc-agent/
├── Manual_Test_Cases/
│   └── run-XXXXX_manual_tests.xlsx
├── Automation_Scripts/
│   ├── package.json
│   ├── playwright.config.ts
│   └── tests/
│       ├── story_001.spec.ts
│       ├── story_002.spec.ts
│       └── ...
├── Results/
│   ├── run-XXXXX_results.json
│   ├── run-XXXXX_results.html
│   └── screenshots/
└── ...
```

## 🎯 Benefits

1. **Granular Control**: User controls each step
2. **Clear Workflow**: Visual progression through steps
3. **Test Healing**: AI-powered failure resolution
4. **Better Organization**: Separate folders for each artifact type
5. **Progressive Enhancement**: Only run what's needed

## 🚀 Implementation Priority

1. **HIGH**: Backend endpoints (manual, automation, execute)
2. **HIGH**: JavaScript handlers and state management
3. **MEDIUM**: Test healing with Claude analysis
4. **LOW**: Advanced features (parallel execution, smart healing)

## 🔧 Technical Notes

- Use existing `write_manual_tests_xlsx()` function
- Use existing `write_playwright_suite()` function
- Leverage Playwright's JSON reporter for structured results
- Use Claude API for intelligent test healing
- Implement proper error handling for each step
