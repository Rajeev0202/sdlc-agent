# Harness Integration Migration Summary

## What Changed

The SDLC Agent now has **integrated harness features** built directly into the Python codebase. This eliminates dependency on external JavaScript hooks while providing enhanced observability and control.

## New Components

### 1. Core Harness (`sdlc_agent/harness.py`)
- **`Harness` class**: Main harness with observability, state, metrics
- **`get_harness()`**: Get global harness instance
- **`HarnessConfig`**: Configuration from `.claude/settings.json`
- **Models**: `ToolSpan`, `LogEntry`, `Metrics`, `SDLCState`

### 2. Hooks Integration (`sdlc_agent/hooks.py`)
Python-based hooks that replace JS files:
- `on_stage_transition` - replaces `on-agent-stop.js`
- `on_jira_card_created` - replaces `on-jira-create.js`
- `on_coverage_measured` - new
- `on_git_push_attempt` - replaces `pre-push-gate.js`
- `register_default_hooks()` - convenience function

### 3. Updated Orchestrator
- `use_harness` parameter (default `True`)
- Automatic span tracking for all stages
- Structured logging throughout pipeline
- Stage transitions recorded

### 4. CLI Enhancements
- `status` - Show pipeline status + metrics
- `observe [report]` - View observability reports

## File Mapping

| Old (JS Hooks) | New (Python) | Status |
|----------------|--------------|--------|
| `.claude/hooks/on-tool-start.js` | `harness.tool_span()` | ✅ Replaced |
| `.claude/hooks/on-tool-use.js` | Auto span completion | ✅ Replaced |
| `.claude/hooks/on-agent-stop.js` | `on_stage_transition` | ✅ Replaced |
| `.claude/hooks/on-jira-create.js` | `on_jira_card_created` | ✅ Replaced |
| `.claude/hooks/pre-push-gate.js` | `on_git_push_attempt` | ✅ Replaced |
| `.claude/hooks/sdlc-observe.js` | `cli observe` command | ⚠️ Kept for Node reports |

**Note**: JS hooks can be kept (backward compatible) or removed. Python harness works independently.

## Usage Changes

### Before (External Hooks)
```bash
# Hooks run automatically via .claude/settings.json
# No programmatic access
# Must parse .claude/sdlc-state.json manually
```

### After (Integrated Harness)
```python
from sdlc_agent import get_harness, register_default_hooks

# Get harness
harness = get_harness()
register_default_hooks(harness)

# Access state
print(harness.state.stage)
print(harness.state.coverage_pct)

# Log events
harness.log(Severity.INFO, "Message")

# Track operations
with harness.tool_span("operation"):
    result = do_work()

# Check gates
can_push, reason = harness.can_advance_to("commit")
```

## Configuration

### `.claude/settings.json`
New environment variables recognized by harness:

```json
{
  "env": {
    "COVERAGE_THRESHOLD": "80",
    "AUTO_ADVANCE_STAGES": "false",
    "ENABLE_OBSERVABILITY": "true",
    "ENABLE_HOOKS": "true"
  }
}
```

## Observability

### Before
- JS hooks write to `.claude/observability/`
- View with `node .claude/hooks/sdlc-observe.js`

### After
- Python harness writes to `.claude/observability/`
- View with `python -m sdlc_agent.cli observe [report]`
- **OR** still use `node .claude/hooks/sdlc-observe.js` (compatible)

## Testing

### Before
```python
# No easy way to test hooks
# State in JSON must be manually created
```

### After
```python
from sdlc_agent import reset_harness, get_harness

def test_pipeline():
    reset_harness()  # Clean slate
    harness = get_harness()

    # Full programmatic control
    harness.state.stage = "test"
    harness.transition_to("build")

    assert harness.state.stage == "build"
```

## Migration Steps

### For Existing Projects

1. **Update imports**:
   ```python
   from sdlc_agent import get_harness, register_default_hooks
   ```

2. **Initialize harness** (one-time, at startup):
   ```python
   harness = get_harness()
   register_default_hooks(harness)
   ```

3. **Use orchestrator** (harness auto-enabled):
   ```python
   orchestrator = Orchestrator(use_harness=True)
   ```

4. **Optional**: Remove JS hooks if not using Node observability

### For New Projects

1. Copy `.claude/settings.json` template
2. Use `Orchestrator(use_harness=True)` (default)
3. Access harness via `get_harness()` when needed
4. Run `python -m sdlc_agent.cli status` to verify

## Benefits Summary

✅ **Single Language** - No JS/Python context switching  
✅ **Type Safety** - Pydantic models ensure data integrity  
✅ **Testability** - Easy unit testing of hooks and state  
✅ **Performance** - No subprocess overhead  
✅ **Portability** - Works anywhere Python runs (no Node required)  
✅ **Visibility** - Full programmatic access to state  
✅ **Debugging** - Python stack traces for hook errors  

## Backward Compatibility

The harness integration is **opt-in** via `use_harness` parameter:

```python
# Use integrated harness (recommended)
orchestrator = Orchestrator(use_harness=True)

# Disable harness (legacy mode)
orchestrator = Orchestrator(use_harness=False)
```

JS hooks can remain in place. They work independently of the Python harness.

## Examples

See:
- [`docs/HARNESS_INTEGRATION.md`](docs/HARNESS_INTEGRATION.md) - Full guide
- [`examples/harness_demo.py`](examples/harness_demo.py) - Interactive demo

Run demo:
```bash
python examples/harness_demo.py
```

## Troubleshooting

### "Harness not tracking spans"
Ensure observability is enabled:
```python
harness = get_harness()
print(harness.config.enable_observability)  # Should be True
```

### "Coverage gate not working"
Register hooks:
```python
from sdlc_agent import register_default_hooks
register_default_hooks(get_harness())
```

### "State not persisting"
Use transition methods that auto-save:
```python
harness.transition_to("new_stage")  # Saves automatically
# Instead of:
# harness.state.stage = "new_stage"  # Requires manual save
```

## Support

- See full documentation: [`docs/HARNESS_INTEGRATION.md`](docs/HARNESS_INTEGRATION.md)
- Run demo: `python examples/harness_demo.py`
- View status: `python -m sdlc_agent.cli status`
- View metrics: `python -m sdlc_agent.cli observe metrics`
