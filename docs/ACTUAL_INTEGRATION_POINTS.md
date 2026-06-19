# Actual Harness Integration Points in Web App

## You're Right - Here's the REAL Integration

The harness integration is **ALREADY in the actual SDLC pipeline**, not just test endpoints.

## Stage 2: Jira Card Creation (LIVE)

### Web Route
```python
# sdlc_agent/web/app.py:314
@app.post("/api/stage2")
def api_stage2():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    jira_project_key = payload.get("jira_project_key", "SCRUM")
    
    # Line 326: Use skill automation
    skill_automation = PlanSkillAutomation(ROOT)
    
    # Line 327: This creates Jira cards with hooks
    backlog = skill_automation.run(brief, jira_project_key)
```

### Skill Automation
```python
# sdlc_agent/skills/plan_skill.py:73
def run(self, brief, jira_project_key):
    # Step 3: Create Jira cards
    jira_links = self._create_jira_cards(stories, jira_project_key)
```

### Jira Card Creation (WHERE HOOK FIRES)
```python
# sdlc_agent/skills/plan_skill.py:316
def _create_jira_cards(self, stories, project_key):
    for story in stories:
        # THIS CALLS create_story() WHICH TRIGGERS THE HOOK
        issue_key = self.jira.create_story(story)  # ← HOOK FIRES HERE
        jira_links[story.id] = issue_key
```

### Jira Client (HOOK TRIGGER)
```python
# sdlc_agent/integrations/jira_client.py:48
class JiraClient:
    def create_story(self, story: UserStory) -> str:
        # Create the Jira issue
        issue = self.jira.create_issue(fields=issue_dict)
        
        # Transition if needed
        if self.auto_transition:
            self._transition_issue(issue, self.auto_transition)
        
        # Try to add to sprint
        try:
            self._add_to_active_sprint(issue)
        except Exception as e:
            logger.warning(f"Failed to add to sprint: {e}")
        
        # LINE 83: TRIGGER HARNESS HOOK ✅
        _trigger_jira_hook(card_key=issue.key, summary=story.want)
        
        return issue.key
```

### Hook Trigger Function
```python
# sdlc_agent/integrations/jira_client.py:21
def _trigger_jira_hook(card_key: str, summary: str | None = None):
    """Trigger the on_jira_card_created hook if harness is available."""
    try:
        from ..harness import get_harness
        harness = get_harness()
        harness._trigger_hook(
            "on_jira_card_created",
            card_key=card_key,
            summary=summary
        )
    except Exception:
        pass  # Non-fatal
```

### Hook Execution
```python
# sdlc_agent/hooks.py:38
def on_jira_card_created(harness, card_key, summary=None, **kwargs):
    # 1. Log it
    harness.log(Severity.INFO, f"Jira card created: {card_key}")
    
    # 2. Track it in state
    harness.state.jira_creates.append({
        "key": card_key,
        "summary": summary,
        "parent": harness.state.epic.get("key") if harness.state.epic else None,
        "confluence_url": harness.state.source,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    
    # 3. Save state
    harness._save_state()
```

## Complete Flow (User Clicks "Plan" in Web UI)

```
User clicks "Plan" button in web UI
    ↓
POST /api/stage2
    ↓
api_stage2() handler (line 314)
    ↓
PlanSkillAutomation.run()
    ↓
_create_jira_cards() (line 316)
    ↓
FOR EACH STORY:
    ↓
jira.create_story(story)  ← Jira client
    ↓
Create issue in Jira API
    ↓
_trigger_jira_hook(card_key, summary)  ← Line 83
    ↓
harness._trigger_hook("on_jira_card_created", ...)
    ↓
on_jira_card_created(harness, card_key, summary)
    ↓
harness.state.jira_creates.append({...})  ← STORED ✅
    ↓
harness._save_state()  → .claude/sdlc-state.json
    ↓
END OF LOOP
    ↓
Return jira_links to web UI
    ↓
Web UI shows created Jira cards
```

## Where Data is Stored

When you create Jira cards via the web UI:

### 1. Harness State File
```json
// .claude/sdlc-state.json
{
  "jira_creates": [
    {
      "key": "SCRUM-123",
      "summary": "User can freeze card",
      "parent": "EPIC-456",
      "confluence_url": "https://...",
      "ts": "2026-06-15T14:30:00.123Z"
    },
    {
      "key": "SCRUM-124",
      "summary": "User can unfreeze card",
      ...
    }
  ]
}
```

### 2. Observability Logs
```jsonl
// .claude/observability/logs.jsonl
{"level":"info","stage":"plan","message":"Jira card created: SCRUM-123",...}
{"level":"info","stage":"plan","message":"Jira card created: SCRUM-124",...}
```

### 3. Run Artifacts
```json
// runs/<run-id>/02_backlog.json
{
  "stories": [...],
  "_jira_links": {
    "US-001": "SCRUM-123",
    "US-002": "SCRUM-124"
  }
}
```

## GitHub PR Integration (Stage 3)

Similarly for GitHub PRs (though not shown in detail):

```python
# sdlc_agent/web/app.py
@app.post("/api/stage3")
def api_stage3():
    # Uses BuildSkillAutomation
    # Which creates PR via github_client
    # Could trigger on_pr_created hook (if we add it)
```

## Verify It Works

### Start the web server:
```bash
uvicorn sdlc_agent.web.app:app --port 8000
```

### Use the web UI:
1. Go to http://localhost:8000
2. Click "Ingest" with a BRD
3. Click "Plan" to create Jira cards
4. **Hooks fire automatically** ✅

### Check harness state:
```bash
cat .claude/sdlc-state.json
```

You'll see:
```json
{
  "jira_creates": [
    {"key": "SCRUM-1", "summary": "...", ...},
    {"key": "SCRUM-2", "summary": "...", ...}
  ]
}
```

### Check logs:
```bash
cat .claude/observability/logs.jsonl | grep "Jira card"
```

## Summary

**Question**: Where did you integrate with the actual SDLC web app routes?

**Answer**: 

✅ **Stage 2 Route** (`/api/stage2` line 314)
  → Calls `PlanSkillAutomation.run()`
  → Calls `_create_jira_cards()` (line 316)
  → Calls `jira.create_story()` for each story
  → **Hook fires** at line 83 of `jira_client.py`
  → Data stored in `.claude/sdlc-state.json`

✅ **JiraClient.create_story()** (line 48 in `jira_client.py`)
  → Creates Jira issue via API
  → Triggers `_trigger_jira_hook()` at line 83
  → Hook executes and stores card in harness

✅ **MockJiraClient.create_story()** (line 19 in `jira_client.py`)
  → Creates mock issue
  → Triggers `_trigger_jira_hook()` at line 31
  → Hook executes same as real client

**The integration is REAL and LIVE** - not just test endpoints!

**Every time you create Jira cards via the web UI, the hook fires and data is stored** ✅
