# Build & Test Phase Harness Integration

## ✅ NOW INTEGRATED!

All SDLC phases now have harness tracking:

| Phase | Route | Hook | Tracks |
|-------|-------|------|--------|
| **Stage 2: Plan** | `/api/stage2` | `on_jira_card_created` | Jira cards created |
| **Stage 3: Build** | `/api/stage3` | `on_pr_created` | PRs and code generated |
| **Stage 5: Test** | `/api/stage5` | `on_tests_generated` | Test files created |

## Stage 3: Build Phase (PR Creation)

### Web Route Integration

```python
# sdlc_agent/web/app.py:415
@app.post("/api/stage3")
def api_stage3():
    # Generate code
    skill_automation = BuildSkillAutomation(ROOT)
    pr = skill_automation.run(backlog, inject_defect=inject)
    
    # Save PR
    _write_json(rd / "03_pr.json", pr)
    
    # ✅ TRIGGER HOOK (NEW)
    harness = get_harness()
    harness._trigger_hook(
        "on_pr_created",
        pr_number=pr.number,
        branch=pr.branch,
        files_count=len(pr.files)
    )
```

### Hook Implementation

```python
# sdlc_agent/hooks.py:91
def on_pr_created(harness, pr_number, branch, files_count, **kwargs):
    # Log it
    harness.log(INFO, f"PR created: #{pr_number} on {branch}")
    
    # Track it
    harness.state.prs_created.append({
        "pr_number": pr_number,
        "branch": branch,
        "files_count": files_count,
        "ts": "2026-06-15T..."
    })
    
    # Save it
    harness._save_state()
```

### Data Stored

```json
// .claude/sdlc-state.json
{
  "prs_created": [
    {
      "pr_number": 1,
      "branch": "feature/card-freeze",
      "files_count": 5,
      "ts": "2026-06-15T14:30:00Z"
    }
  ]
}
```

## Stage 5: Test Phase (Test Generation)

### Web Route Integration

```python
# sdlc_agent/web/app.py:534
@app.post("/api/stage5")
def api_stage5():
    # Generate tests
    suite = stage5_tests.run(pr, backlog)
    _write_json(rd / "05_tests.json", suite)
    
    # ✅ TRIGGER HOOK (NEW)
    harness = get_harness()
    harness._trigger_hook(
        "on_tests_generated",
        test_files_count=len(suite.files),
        coverage_map=suite.coverage_map
    )
```

### Hook Implementation

```python
# sdlc_agent/hooks.py:108
def on_tests_generated(harness, test_files_count, coverage_map, **kwargs):
    # Log it
    harness.log(INFO, f"Tests generated: {test_files_count} files")
    
    # Track it
    harness.state.test_generations.append({
        "test_files_count": test_files_count,
        "coverage_map_count": len(coverage_map),
        "ts": "2026-06-15T..."
    })
    
    # Save it
    harness._save_state()
```

### Data Stored

```json
// .claude/sdlc-state.json
{
  "test_generations": [
    {
      "test_files_count": 3,
      "coverage_map_count": 5,
      "ts": "2026-06-15T14:45:00Z"
    }
  ]
}
```

## Complete SDLC Pipeline Tracking

When you run the full pipeline in the web UI:

```json
// .claude/sdlc-state.json
{
  "stage": "deploy",
  "epic": {"key": "EPIC-123", "summary": "Card Freeze Feature"},
  
  // Stage 2: Jira cards created
  "jira_creates": [
    {"key": "SCRUM-1", "summary": "User can freeze card", ...},
    {"key": "SCRUM-2", "summary": "User can unfreeze card", ...}
  ],
  
  // Stage 3: PR created
  "prs_created": [
    {"pr_number": 1, "branch": "feature/card-freeze", "files_count": 5, ...}
  ],
  
  // Stage 5: Tests generated
  "test_generations": [
    {"test_files_count": 3, "coverage_map_count": 5, ...}
  ],
  
  // Coverage measurement
  "coverage_pct": 85.0,
  
  // Audit trail
  "history": [
    {"stage": "ingest", "ts": "..."},
    {"stage": "plan", "ts": "..."},
    {"stage": "build", "ts": "..."},
    {"stage": "test", "ts": "..."},
    {"stage": "deploy", "ts": "..."}
  ]
}
```

## Registered Hooks

All 6 hooks are now registered:

```python
# sdlc_agent/hooks.py:123
def register_default_hooks(harness):
    harness.register_hook("on_stage_transition", on_stage_transition)
    harness.register_hook("on_jira_card_created", on_jira_card_created)
    harness.register_hook("on_pr_created", on_pr_created)           # ← NEW
    harness.register_hook("on_tests_generated", on_tests_generated) # ← NEW
    harness.register_hook("on_coverage_measured", on_coverage_measured)
    harness.register_hook("on_git_push_attempt", on_git_push_attempt)
```

## Verify All Hooks

```bash
# Start web server
uvicorn sdlc_agent.web.app:app --port 8000

# Check hooks registered
curl http://localhost:8000/api/harness/status | python -m json.tool
```

Expected:
```json
{
  "hooks_registered": true,
  "hook_events": [
    "on_stage_transition",
    "on_jira_card_created",
    "on_pr_created",           ← NEW
    "on_tests_generated",      ← NEW
    "on_coverage_measured",
    "on_git_push_attempt"
  ],
  "hook_counts": {
    "on_jira_card_created": 1,
    "on_pr_created": 1,        ← NEW
    "on_tests_generated": 1    ← NEW
  }
}
```

## Run Full Pipeline

```bash
# In web UI:
1. Ingest BRD
2. Plan (creates Jira cards)  → on_jira_card_created fires ✅
3. Build (creates PR)          → on_pr_created fires ✅
4. Review
5. Test (generates tests)      → on_tests_generated fires ✅
6. Deploy

# Check harness state
cat .claude/sdlc-state.json
```

You'll see all tracking data:
- `jira_creates`: Cards from Stage 2
- `prs_created`: PRs from Stage 3
- `test_generations`: Tests from Stage 5

## Observability Logs

```bash
cat .claude/observability/logs.jsonl | grep -E "Jira|PR|Test"
```

Output:
```jsonl
{"level":"info","message":"Jira card created: SCRUM-1",...}
{"level":"info","message":"Jira card created: SCRUM-2",...}
{"level":"info","message":"PR created: #1 on feature/card-freeze (5 files)",...}
{"level":"info","message":"Tests generated: 3 test files created",...}
```

## Summary

**Question**: During Build and Test phases, is harness tracking created?

**Answer**: **YES! ✅ NOW INTEGRATED**

### Stage 2 (Plan): ✅ 
- **Hook**: `on_jira_card_created`
- **Tracks**: Every Jira card created
- **Route**: `/api/stage2` line 327

### Stage 3 (Build): ✅ **NEW**
- **Hook**: `on_pr_created`
- **Tracks**: PR number, branch, files count
- **Route**: `/api/stage3` line 421

### Stage 5 (Test): ✅ **NEW**
- **Hook**: `on_tests_generated`
- **Tracks**: Test files count, coverage map
- **Route**: `/api/stage5` line 536

All data is stored in `.claude/sdlc-state.json` and logged to `.claude/observability/logs.jsonl`! 🎉
