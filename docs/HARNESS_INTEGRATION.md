# Harness Integration Guide

The SDLC Agent now has **integrated harness features** built directly into the Python codebase, eliminating the need for external JavaScript hooks while providing enhanced observability, state management, and lifecycle control.

## What's Integrated

### 1. **Observability**
- **Distributed Tracing**: Every tool call is tracked with trace_id and span_id
- **Structured Logging**: All stages emit structured logs with severity levels
- **Metrics Dashboard**: Aggregated metrics by stage, tool, and error rate
- **Performance Tracking**: Tool call duration and slowest operations

All observability data is written to `.claude/observability/`:
- `traces.jsonl` - tool execution spans
- `logs.jsonl` - structured log entries
- `metrics.json` - aggregated metrics

### 2. **State Management**
Unified state in `.claude/sdlc-state.json` that tracks:
- Current stage and persona
- Pipeline history and audit trail
- Jira cards created
- Coverage metrics
- Errors and open questions

### 3. **Lifecycle Hooks**
Programmatic hooks in Python (not JavaScript):
- `on_stage_transition` - fires when moving between stages
- `on_jira_card_created` - fires when Jira cards are created
- `on_coverage_measured` - fires when test coverage is measured
- `on_git_push_attempt` - fires before git push (can block)

### 4. **Quality Gates**
Built-in gates that enforce NatWest standards:
- Coverage threshold (default 80%)
- Stage transition validation
- Permission checks

## Usage

### Basic Usage

```python
from sdlc_agent import get_harness, register_default_hooks

# Get global harness instance
harness = get_harness()

# Register default hooks
register_default_hooks(harness)

# Use context manager for automatic span tracking
with harness.tool_span("my_operation"):
    # Your code here
    result = do_something()

# Manual logging
from sdlc_agent import Severity
harness.log(Severity.INFO, "Operation completed")

# Transition stages
harness.transition_to("build", persona="Amelia")

# Check if can advance
can_advance, reason = harness.can_advance_to("commit")
if not can_advance:
    print(f"Blocked: {reason}")
```

### Running with Harness

The orchestrator automatically uses the harness when `use_harness=True` (default):

```python
from sdlc_agent.orchestrator import Orchestrator

orchestrator = Orchestrator(use_harness=True)
result = orchestrator.run("path/to/brd.md")
```

### CLI Commands

```bash
# Show pipeline status with metrics
python -m sdlc_agent.cli status

# View observability reports
python -m sdlc_agent.cli observe metrics
python -m sdlc_agent.cli observe traces --limit 50
python -m sdlc_agent.cli observe errors
python -m sdlc_agent.cli observe slow --limit 10
```

### Custom Hooks

Register your own hooks:

```python
def my_custom_hook(harness, **kwargs):
    print(f"Stage changed to: {harness.state.stage}")
    # Custom logic here

harness.register_hook("on_stage_transition", my_custom_hook)
```

## Configuration

Configure via `.claude/settings.json`:

```json
{
  "env": {
    "SDLC_AGENT_RUNS_DIR": "./runs",
    "COVERAGE_THRESHOLD": "80",
    "AUTO_ADVANCE_STAGES": "false",
    "ENABLE_OBSERVABILITY": "true",
    "ENABLE_HOOKS": "true"
  }
}
```

## Migration from JS Hooks

The integrated harness **replaces** the JavaScript hooks in `.claude/hooks/`:

| Old JS Hook | New Python Hook |
|-------------|-----------------|
| `on-tool-start.js` | `harness.tool_span()` context manager |
| `on-tool-use.js` | Automatic span completion |
| `on-agent-stop.js` | `harness.transition_to()` |
| `on-jira-create.js` | `on_jira_card_created` hook |
| `pre-push-gate.js` | `on_git_push_attempt` hook |
| `sdlc-observe.js` | `python -m sdlc_agent.cli observe` |

You can **keep or remove** the JS hooks - the Python harness works independently.

## Benefits

1. **Single Language**: No context switching between Python and JavaScript
2. **Type Safety**: Pydantic models ensure data integrity
3. **Testability**: Easier to unit test hooks and state transitions
4. **Performance**: No subprocess overhead for hook execution
5. **Portability**: Works anywhere Python runs (no Node.js required)
6. **Visibility**: Full access to harness state from Python code

## Example: Full Pipeline with Harness

```python
from sdlc_agent import get_harness, register_default_hooks, Severity
from sdlc_agent.orchestrator import Orchestrator

# Initialize
harness = get_harness()
register_default_hooks(harness)

# Set up initial state
harness.state.epic = {
    "key": "EPIC-123",
    "summary": "Card Freeze Feature"
}
harness._save_state()

# Run pipeline
orchestrator = Orchestrator(use_harness=True)

try:
    result = orchestrator.run(
        "samples/brd_natwest_card_freeze.md",
        approver="po@natwest.com"
    )

    # Check results
    if result.decision and result.decision.go:
        harness.log(Severity.INFO, "🎉 Pipeline GO - ready to deploy!")
        print(harness.render_status())
    else:
        harness.log(Severity.WARN, "Pipeline NO-GO - see blocking reasons")
        for reason in result.decision.blocking_reasons:
            print(f"  ❌ {reason}")

finally:
    # Show metrics
    print("\n=== Pipeline Metrics ===")
    metrics = harness.metrics
    print(f"Tool calls: {metrics.totals.get('tool_calls', 0)}")
    print(f"Errors: {metrics.totals.get('errors', 0)}")
    print(f"Error rate: {metrics.totals.get('error_rate_pct', 0)}%")
```

## Observability Dashboard

The harness tracks all operations. View the dashboard:

```bash
# Summary report (metrics + recent errors + slow tools)
python -m sdlc_agent.cli observe

# Detailed metrics
python -m sdlc_agent.cli observe metrics

# Recent trace spans
python -m sdlc_agent.cli observe traces --limit 100

# All errors
python -m sdlc_agent.cli observe errors

# Slowest tool calls
python -m sdlc_agent.cli observe slow --limit 20
```

## Testing

The harness can be reset between tests:

```python
from sdlc_agent import reset_harness

def test_pipeline():
    reset_harness()  # Clean slate
    harness = get_harness()
    # ... run tests
```

## Troubleshooting

### Observability data not being written

Check configuration:
```python
harness = get_harness()
print(harness.config.enable_observability)  # Should be True
print(harness.config.observability_dir)     # Should exist
```

### Coverage gate blocking push

Check current coverage:
```python
harness = get_harness()
print(f"Coverage: {harness.state.coverage_pct}%")
print(f"Threshold: {harness.config.coverage_threshold}%")
```

Adjust threshold in `.claude/settings.json`:
```json
{"env": {"COVERAGE_THRESHOLD": "70"}}
```

### State not persisting

Ensure you're calling `_save_state()` after modifications:
```python
harness.state.stage = "new_stage"
harness._save_state()  # Required!
```

Better: use the transition method which saves automatically:
```python
harness.transition_to("new_stage")  # Saves automatically
```
