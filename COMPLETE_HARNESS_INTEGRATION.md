# Complete Harness Integration - All SDLC Stages

## ✅ ALL STAGES NOW INTEGRATED!

Every stage in the SDLC pipeline now has harness tracking:

| Stage | Route | Hook | Tracks |
|-------|-------|------|--------|
| **1: Ingest/Brainstorm** | `/api/stage1` | `on_requirements_ingested` | BRD source, stories, questions |
| **2: Plan** | `/api/stage2` | `on_jira_card_created` | Jira cards created |
| **3: Build** | `/api/stage3` | `on_pr_created` | PR, branch, code files |
| **4: Review** | `/api/stage4` | *(uses stage_transition)* | Review findings |
| **5: Test** | `/api/stage5` | `on_tests_generated` | Test files, coverage |
| **6: Deploy** | `/api/stage6` | `on_coverage_measured` | Final coverage, gates |

## Stage 1: Brainstorming (Requirement Ingestion)

### Web Route
```python
# sdlc_agent/web/app.py:182
@app.post("/api/stage1")
def api_stage1():
    # Ingest from Confluence/file
    skill_automation = IngestSkillAutomation(ROOT)
    skill_state = skill_automation.run(source)
    
    # ✅ TRIGGER HOOK
    harness._trigger_hook(
        "on_requirements_ingested",
        source=source,
        stories_found=len(skill_state.get("stories", [])),
        open_questions=len(skill_state.get("open_questions", []))
    )
```

### Hook
```python
# sdlc_agent/hooks.py:91
def on_requirements_ingested(harness, source, stories_found, open_questions):
    harness.log(INFO, f"Requirements ingested from {source}")
    
    harness.state.requirements_ingested.append({
        "source": source,
        "stories_found": stories_found,
        "open_questions": open_questions,
        "ts": "2026-06-15T..."
    })
```

### Data Stored
```json
{
  "requirements_ingested": [
    {
      "source": "https://confluence.example.com/page/123",
      "stories_found": 3,
      "open_questions": 5,
      "ts": "2026-06-15T14:00:00Z"
    }
  ]
}
```

## Stage 2: Planning (Jira Cards)

### Web Route
```python
# sdlc_agent/web/app.py:314
@app.post("/api/stage2")
def api_stage2():
    skill_automation = PlanSkillAutomation(ROOT)
    backlog = skill_automation.run(brief, jira_project_key)
    # Hook triggered inside PlanSkillAutomation
```

### Skill Automation
```python
# sdlc_agent/skills/plan_skill.py:316
def _create_jira_cards(self, stories, project_key):
    for story in stories:
        issue_key = self.jira.create_story(story)  # ✅ Hook fires here
```

### Jira Client
```python
# sdlc_agent/integrations/jira_client.py:83
def create_story(self, story):
    issue = self.jira.create_issue(...)
    
    # ✅ TRIGGER HOOK
    _trigger_jira_hook(card_key=issue.key, summary=story.want)
```

### Hook
```python
# sdlc_agent/hooks.py:30
def on_jira_card_created(harness, card_key, summary):
    harness.log(INFO, f"Jira card created: {card_key}")
    
    harness.state.jira_creates.append({
        "key": card_key,
        "summary": summary,
        "parent": harness.state.epic.get("key"),
        "ts": "..."
    })
```

### Data Stored
```json
{
  "jira_creates": [
    {
      "key": "SCRUM-123",
      "summary": "User can freeze card",
      "parent": "EPIC-456",
      "ts": "2026-06-15T14:15:00Z"
    }
  ]
}
```

## Stage 3: Build (Code/PR Generation)

### Web Route
```python
# sdlc_agent/web/app.py:404
@app.post("/api/stage3")
def api_stage3():
    skill_automation = BuildSkillAutomation(ROOT)
    pr = skill_automation.run(backlog, inject_defect=inject)
    
    # ✅ TRIGGER HOOK
    harness._trigger_hook(
        "on_pr_created",
        pr_number=pr.number,
        branch=pr.branch,
        files_count=len(pr.files)
    )
```

### Hook
```python
# sdlc_agent/hooks.py:108
def on_pr_created(harness, pr_number, branch, files_count):
    harness.log(INFO, f"PR created: #{pr_number} on {branch}")
    
    harness.state.prs_created.append({
        "pr_number": pr_number,
        "branch": branch,
        "files_count": files_count,
        "ts": "..."
    })
```

### Data Stored
```json
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

## Stage 5: Test (Test Generation)

### Web Route
```python
# sdlc_agent/web/app.py:529
@app.post("/api/stage5")
def api_stage5():
    suite = stage5_tests.run(pr, backlog)
    
    # ✅ TRIGGER HOOK
    harness._trigger_hook(
        "on_tests_generated",
        test_files_count=len(suite.files),
        coverage_map=suite.coverage_map
    )
```

### Hook
```python
# sdlc_agent/hooks.py:125
def on_tests_generated(harness, test_files_count, coverage_map):
    harness.log(INFO, f"Tests generated: {test_files_count} files")
    
    harness.state.test_generations.append({
        "test_files_count": test_files_count,
        "coverage_map_count": len(coverage_map),
        "ts": "..."
    })
```

### Data Stored
```json
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

## Complete Pipeline Data

After running full SDLC pipeline in web UI:

```json
// .claude/sdlc-state.json
{
  "stage": "deploy",
  "trace_id": "trace-abc123",
  "epic": {
    "key": "EPIC-456",
    "summary": "Card Freeze Feature"
  },
  
  // Stage 1: Requirements ingested
  "requirements_ingested": [
    {
      "source": "https://confluence.example.com/page/123",
      "stories_found": 3,
      "open_questions": 5,
      "ts": "2026-06-15T14:00:00Z"
    }
  ],
  
  // Stage 2: Jira cards created
  "jira_creates": [
    {"key": "SCRUM-123", "summary": "User can freeze card", ...},
    {"key": "SCRUM-124", "summary": "User can unfreeze card", ...},
    {"key": "SCRUM-125", "summary": "Audit freeze events", ...}
  ],
  
  // Stage 3: PR created
  "prs_created": [
    {
      "pr_number": 1,
      "branch": "feature/card-freeze",
      "files_count": 5,
      "ts": "2026-06-15T14:30:00Z"
    }
  ],
  
  // Stage 5: Tests generated
  "test_generations": [
    {
      "test_files_count": 3,
      "coverage_map_count": 5,
      "ts": "2026-06-15T14:45:00Z"
    }
  ],
  
  // Coverage measurement
  "coverage_pct": 85.0,
  
  // Stage transitions
  "history": [
    {"stage": "ingest", "persona": "Winston", "ts": "2026-06-15T14:00:00Z"},
    {"stage": "plan", "persona": "Priya", "ts": "2026-06-15T14:15:00Z"},
    {"stage": "build", "persona": "Amelia", "ts": "2026-06-15T14:30:00Z"},
    {"stage": "review", "persona": "Devon", "ts": "2026-06-15T14:40:00Z"},
    {"stage": "test", "persona": "Quinn", "ts": "2026-06-15T14:45:00Z"},
    {"stage": "deploy", "persona": "Marcus", "ts": "2026-06-15T15:00:00Z"}
  ],
  
  "timestamp": "2026-06-15T15:00:00Z"
}
```

## All Registered Hooks

```python
# sdlc_agent/hooks.py:140
def register_default_hooks(harness):
    harness.register_hook("on_stage_transition", on_stage_transition)
    harness.register_hook("on_requirements_ingested", on_requirements_ingested)  # Stage 1
    harness.register_hook("on_jira_card_created", on_jira_card_created)         # Stage 2
    harness.register_hook("on_pr_created", on_pr_created)                       # Stage 3
    harness.register_hook("on_tests_generated", on_tests_generated)             # Stage 5
    harness.register_hook("on_coverage_measured", on_coverage_measured)         # Stage 6
    harness.register_hook("on_git_push_attempt", on_git_push_attempt)           # Gate
```

## Verify Complete Integration

```bash
# Start web server
uvicorn sdlc_agent.web.app:app --port 8000

# Check all hooks registered
curl http://localhost:8000/api/harness/status | python -m json.tool
```

Expected:
```json
{
  "hooks_registered": true,
  "hook_events": [
    "on_stage_transition",
    "on_requirements_ingested",   ✅ Stage 1
    "on_jira_card_created",       ✅ Stage 2
    "on_pr_created",              ✅ Stage 3
    "on_tests_generated",         ✅ Stage 5
    "on_coverage_measured",
    "on_git_push_attempt"
  ],
  "hook_counts": {
    "on_requirements_ingested": 1,
    "on_jira_card_created": 1,
    "on_pr_created": 1,
    "on_tests_generated": 1,
    "on_coverage_measured": 1,
    "on_git_push_attempt": 1
  }
}
```

## Observability Logs

After running complete pipeline:

```bash
cat .claude/observability/logs.jsonl
```

Shows:
```jsonl
{"level":"info","message":"Requirements ingested from https://...","tool":"requirement_ingest",...}
{"level":"info","message":"Jira card created: SCRUM-123","tool":"jira_create",...}
{"level":"info","message":"Jira card created: SCRUM-124","tool":"jira_create",...}
{"level":"info","message":"PR created: #1 on feature/card-freeze (5 files)","tool":"pr_create",...}
{"level":"info","message":"Tests generated: 3 test files created","tool":"test_generation",...}
{"level":"info","message":"Coverage gate passed: 85% ≥ 80%","tool":"coverage_check",...}
```

## Summary Table

| Stage | What Happens | Hook Fired | Data Tracked |
|-------|--------------|------------|--------------|
| **1: Ingest** | Load BRD/Confluence | `on_requirements_ingested` | Source, stories, questions |
| **2: Plan** | Create Jira cards | `on_jira_card_created` (per card) | Each card key, summary, parent |
| **3: Build** | Generate code, create PR | `on_pr_created` | PR number, branch, files |
| **4: Review** | Review code | *(stage_transition)* | Review findings in PR |
| **5: Test** | Generate tests | `on_tests_generated` | Test count, coverage map |
| **6: Deploy** | Check gates | `on_coverage_measured` | Final coverage % |

## Complete Flow

```
User runs full pipeline in web UI:

1. POST /api/stage1 (Ingest)
   → on_requirements_ingested fires
   → Data: source, stories_found, open_questions
   
2. POST /api/stage2 (Plan)
   → For each story: on_jira_card_created fires
   → Data: card key, summary, parent epic
   
3. POST /api/approve
   → No hook (approval gate)
   
4. POST /api/stage3 (Build)
   → on_pr_created fires
   → Data: PR number, branch, files count
   
5. POST /api/stage4 (Review)
   → No specific hook (findings in PR)
   
6. POST /api/stage5 (Test)
   → on_tests_generated fires
   → Data: test files count, coverage map
   
7. POST /api/stage6 (Deploy)
   → on_coverage_measured fires
   → Data: coverage percentage

All data saved to: .claude/sdlc-state.json
All logs saved to: .claude/observability/logs.jsonl
All metrics in: .claude/observability/metrics.json
```

## Files Changed

1. **[sdlc_agent/hooks.py](sdlc_agent/hooks.py)** - Added `on_requirements_ingested`, `on_pr_created`, `on_tests_generated`
2. **[sdlc_agent/web/app.py](sdlc_agent/web/app.py)** - Integrated hooks in Stages 1, 3, 5
3. **[sdlc_agent/harness.py](sdlc_agent/harness.py)** - Added state fields: `requirements_ingested`, `prs_created`, `test_generations`
4. **[sdlc_agent/integrations/jira_client.py](sdlc_agent/integrations/jira_client.py)** - Added `_trigger_jira_hook()` in Stage 2

## Result

**Every SDLC stage** now tracks data via harness hooks! 🎉

Run the full pipeline and check `.claude/sdlc-state.json` - you'll see complete tracking from ingestion to deployment!
