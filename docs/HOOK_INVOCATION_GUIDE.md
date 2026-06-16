# Hook Invocation Guide

## How `on_jira_card_created` Hook is Invoked

### Complete Flow

```
1. REGISTRATION (Startup)
   ↓
   register_default_hooks(harness)
   ↓
   harness._hooks["on_jira_card_created"] = [on_jira_card_created]
   

2. EXECUTION (When Card Created)
   ↓
   orchestrator.run()
   ↓
   stage2_stories.run()
   ↓
   jira_client.create_story(story)
   ↓
   _trigger_jira_hook(card_key="DEMO-1", summary="...")
   ↓
   harness._trigger_hook("on_jira_card_created", ...)
   ↓
   on_jira_card_created(harness, card_key="DEMO-1", ...)
   ↓
   
3. RESULT
   ↓
   - Log entry created
   - State updated (jira_creates list)
   - State saved to disk
```

### Code Path

#### Step 1: Registration

```python
# At startup (you call this once)
from sdlc_agent import get_harness, register_default_hooks

harness = get_harness()
register_default_hooks(harness)  # ← Registers all hooks
```

**Inside `register_default_hooks()`**:
```python
# sdlc_agent/hooks.py
def register_default_hooks(harness):
    harness.register_hook("on_jira_card_created", on_jira_card_created)
    harness.register_hook("on_stage_transition", on_stage_transition)
    harness.register_hook("on_coverage_measured", on_coverage_measured)
    harness.register_hook("on_git_push_attempt", on_git_push_attempt)
```

**Inside `harness.register_hook()`**:
```python
# sdlc_agent/harness.py
def register_hook(self, event: str, callback: Callable):
    if event not in self._hooks:
        self._hooks[event] = []
    self._hooks[event].append(callback)
    
# Result:
# harness._hooks = {
#     "on_jira_card_created": [on_jira_card_created],
#     ...
# }
```

#### Step 2: Jira Card Creation

```python
# In Stage 2 or when manually creating cards
jira_client = MockJiraClient()
issue_key = jira_client.create_story(story)
```

**Inside `MockJiraClient.create_story()`**:
```python
# sdlc_agent/integrations/jira_client.py
def create_story(self, story: UserStory) -> str:
    # 1. Create the Jira issue
    issue_key = f"{self.project_key}-{self._issue_counter}"
    self.created_issues[issue_key] = {...}
    
    # 2. Trigger the hook ← NEW
    _trigger_jira_hook(card_key=issue_key, summary=story.want)
    
    return issue_key
```

#### Step 3: Hook Trigger

**Inside `_trigger_jira_hook()`**:
```python
# sdlc_agent/integrations/jira_client.py
def _trigger_jira_hook(card_key: str, summary: str | None = None):
    try:
        from ..harness import get_harness
        harness = get_harness()
        
        # Call the harness trigger method
        harness._trigger_hook(
            "on_jira_card_created",  # Event name
            card_key=card_key,        # Data
            summary=summary
        )
    except Exception:
        # Non-fatal - won't crash if harness unavailable
        pass
```

#### Step 4: Hook Dispatcher

**Inside `harness._trigger_hook()`**:
```python
# sdlc_agent/harness.py
def _trigger_hook(self, event: str, **kwargs):
    if not self.config.enable_hooks:
        return
    
    # Get all callbacks registered for this event
    for callback in self._hooks.get(event, []):
        try:
            # Call each callback with harness + event data
            callback(harness=self, **kwargs)
        except Exception as e:
            # Log error but don't crash
            self.log(Severity.ERROR, f"Hook {event} failed: {e}")
```

#### Step 5: Hook Execution

**Inside `on_jira_card_created()`**:
```python
# sdlc_agent/hooks.py
def on_jira_card_created(harness, card_key, summary=None, **kwargs):
    # 1. Log the event
    harness.log(
        Severity.INFO,
        f"Jira card created: {card_key}",
        tool="jira_create",
    )
    
    # 2. Update state
    harness.state.jira_creates.append({
        "key": card_key,
        "summary": summary,
        "parent": harness.state.epic.get("key") if harness.state.epic else None,
        "confluence_url": harness.state.source,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    
    # 3. Persist to disk
    harness._save_state()
```

### Integration Points

| Location | File | Method | Action |
|----------|------|--------|--------|
| **1. Hook Definition** | `sdlc_agent/hooks.py` | `on_jira_card_created()` | Defines what happens |
| **2. Hook Registration** | `sdlc_agent/hooks.py` | `register_default_hooks()` | Registers hook |
| **3. Hook Trigger** | `sdlc_agent/integrations/jira_client.py` | `_trigger_jira_hook()` | Triggers hook |
| **4. Hook Dispatcher** | `sdlc_agent/harness.py` | `_trigger_hook()` | Calls callbacks |
| **5. Mock Client** | `sdlc_agent/integrations/jira_client.py` | `MockJiraClient.create_story()` | Calls trigger |
| **6. Real Client** | `sdlc_agent/integrations/jira_client.py` | `JiraClient.create_story()` | Calls trigger |

### When Hook is Invoked

The hook is invoked **every time** a Jira card is created through:

1. **Stage 2 (Stories)**: When orchestrator runs stage2_stories
2. **Manual Creation**: When you manually call `jira_client.create_story()`
3. **/sdlc-plan Skill**: When using the planning skill
4. **Any Code Path**: That calls `create_story()` on a Jira client

### What Hook Does

When invoked, `on_jira_card_created`:

1. ✅ Logs "Jira card created: {key}" to observability
2. ✅ Appends card details to `harness.state.jira_creates[]`
3. ✅ Saves state to `.claude/sdlc-state.json`
4. ✅ Associates card with current epic and Confluence source

### Verifying Hook Works

#### Run the Demo
```bash
python examples/jira_hook_demo_simple.py
```

Expected output:
```
Creating Jira Cards...
  -> Hook fired! Card: DEMO-1    ← Custom hook
  -> Hook fired! Card: DEMO-2    ← Custom hook

Final State:
  Total cards created: 2         ← Default hook updated state
  Card History:
    - DEMO-1: freeze card
      Parent: EPIC-123             ← Hook recorded parent
```

#### Check State File
```bash
cat .claude/sdlc-state.json
```

Should show:
```json
{
  "jira_creates": [
    {
      "key": "DEMO-1",
      "summary": "freeze card",
      "parent": "EPIC-123",
      "confluence_url": "https://...",
      "ts": "2026-06-15T14:36:16.123Z"
    }
  ]
}
```

#### Check Logs
```bash
python -m sdlc_agent.cli observe logs
```

Should include:
```
[INFO] [plan] Jira card created: DEMO-1
```

### Custom Hook Example

You can add your own hooks alongside the default:

```python
from sdlc_agent import get_harness, register_default_hooks

harness = get_harness()
register_default_hooks(harness)  # Default hooks

# Add custom hook
def send_slack_notification(harness, card_key, summary=None, **kwargs):
    print(f"Slack: New card {card_key} created!")
    # Your Slack integration here

harness.register_hook("on_jira_card_created", send_slack_notification)

# Now BOTH hooks fire on every card creation:
# 1. on_jira_card_created (default) - updates state
# 2. send_slack_notification (custom) - sends Slack message
```

### Multiple Hooks

Multiple hooks can be registered for the same event:

```python
harness.register_hook("on_jira_card_created", hook1)
harness.register_hook("on_jira_card_created", hook2)
harness.register_hook("on_jira_card_created", hook3)

# When card is created, ALL THREE execute in order:
# 1. hook1(harness, card_key="DEMO-1", ...)
# 2. hook2(harness, card_key="DEMO-1", ...)
# 3. hook3(harness, card_key="DEMO-1", ...)
```

### Hook Failure Handling

Hooks are **non-fatal**:

```python
def buggy_hook(harness, card_key, **kwargs):
    raise Exception("Hook crashed!")

harness.register_hook("on_jira_card_created", buggy_hook)

# Card creation still succeeds:
issue_key = jira.create_story(story)  # Returns "DEMO-1"

# Hook error is logged but doesn't crash the pipeline
# Check: python -m sdlc_agent.cli observe errors
```

### Disabling Hooks

Disable via configuration:

```python
# Option 1: Via config
harness.config.enable_hooks = False

# Option 2: Via settings.json
{
  "env": {
    "ENABLE_HOOKS": "false"
  }
}

# Now hooks won't execute
jira.create_story(story)  # Card created, but hooks don't fire
```

### Testing Hooks

```python
from sdlc_agent import reset_harness, get_harness, register_default_hooks

def test_jira_hook():
    # Clean state
    reset_harness()
    harness = get_harness()
    register_default_hooks(harness)
    
    # Set up context
    harness.state.epic = {"key": "TEST-1"}
    
    # Create card
    jira = MockJiraClient()
    story = UserStory(id="S-001", persona="User", want="feature", 
                      so_that="benefit", acceptance_criteria=["AC"])
    
    issue_key = jira.create_story(story)
    
    # Verify hook worked
    assert len(harness.state.jira_creates) == 1
    assert harness.state.jira_creates[0]["key"] == "SCRUM-1"
    assert harness.state.jira_creates[0]["parent"] == "TEST-1"
```

### Summary

**Question**: How is `on_jira_card_created` invoked?

**Answer**:
1. ✅ **Registered** via `register_default_hooks(harness)` at startup
2. ✅ **Triggered** by `_trigger_jira_hook()` inside `create_story()`
3. ✅ **Dispatched** by `harness._trigger_hook()` to all callbacks
4. ✅ **Executed** as `on_jira_card_created(harness, card_key, summary)`
5. ✅ **Records** card in state and logs to observability

**Flow**: Registration → Card Creation → Trigger → Dispatch → Execute → Record

**Demo**: `python examples/jira_hook_demo_simple.py`

**Test**: `pytest tests/test_jira_hook.py -v`
