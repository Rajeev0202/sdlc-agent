# Quick Start: Integrated Harness

Get started with the integrated harness in 5 minutes.

## 1. Basic Usage

```python
from sdlc_agent import get_harness, register_default_hooks, Severity

# Initialize (once at startup)
harness = get_harness()
register_default_hooks(harness)

# Log a message
harness.log(Severity.INFO, "Starting pipeline")

# Track an operation
with harness.tool_span("my_operation"):
    result = do_work()

# Check current state
print(f"Stage: {harness.state.stage}")
print(f"Trace: {harness.get_or_create_trace_id()}")
```

## 2. Run the Pipeline with Harness

```python
from sdlc_agent.orchestrator import Orchestrator

# Harness enabled by default
orchestrator = Orchestrator()

result = orchestrator.run(
    "samples/brd_natwest_card_freeze.md",
    approver="po@natwest.com"
)

# Check result
if result.decision and result.decision.go:
    print("✅ GO - Ready to deploy")
else:
    print("❌ NO-GO - Issues found")
```

## 3. View Pipeline Status

```bash
# Show current status + metrics
python -m sdlc_agent.cli status

# View detailed metrics
python -m sdlc_agent.cli observe metrics

# View recent traces
python -m sdlc_agent.cli observe traces --limit 50

# View errors
python -m sdlc_agent.cli observe errors
```

## 4. Custom Hooks

```python
def notify_on_stage_change(harness, old_stage, new_stage, **kwargs):
    """Custom hook example."""
    print(f"📢 Stage changed: {old_stage} → {new_stage}")
    # Add your logic: send Slack message, update dashboard, etc.

# Register hook
harness = get_harness()
harness.register_hook("on_stage_transition", notify_on_stage_change)

# Now transitions will trigger your hook
harness.transition_to("build")
```

## 5. Quality Gates

```python
harness = get_harness()

# Set coverage (usually done by test runner)
harness.state.coverage_pct = 85.0

# Check if can proceed
can_push, reason = harness.can_advance_to("commit")
if can_push:
    # Proceed with commit/push
    pass
else:
    print(f"Blocked: {reason}")
```

## 6. Run the Demo

```bash
# Interactive demo showing all features
python examples/harness_demo.py
```

## Configuration

Edit `.claude/settings.json`:

```json
{
  "env": {
    "COVERAGE_THRESHOLD": "80",
    "ENABLE_OBSERVABILITY": "true",
    "ENABLE_HOOKS": "true"
  }
}
```

## Files Created

The harness creates these files:

```
.claude/
├── sdlc-state.json          # Pipeline state
└── observability/
    ├── traces.jsonl         # Tool execution spans
    ├── logs.jsonl           # Structured logs
    └── metrics.json         # Aggregated metrics
```

## Testing

```python
from sdlc_agent import reset_harness, get_harness

def test_my_feature():
    # Clean slate for test
    reset_harness()

    harness = get_harness()
    harness.state.stage = "test"

    # Your test logic
    assert harness.state.stage == "test"
```

## Common Patterns

### Pattern 1: Track Stage Execution

```python
harness = get_harness()
harness.transition_to("build", "Amelia")

with harness.tool_span("compile_code"):
    compile_result = compile()

with harness.tool_span("run_tests"):
    test_result = run_tests()

harness.transition_to("review", "Devon")
```

### Pattern 2: Error Handling

```python
try:
    with harness.tool_span("risky_operation"):
        result = risky_call()
except Exception as e:
    harness.log(
        Severity.ERROR,
        f"Operation failed: {e}",
        tool="risky_operation",
        snippet=str(e)
    )
    raise
```

### Pattern 3: Conditional Advancement

```python
# Check gates before proceeding
can_deploy, reason = harness.can_advance_to("deploy")

if can_deploy:
    deploy_to_production()
else:
    notify_team(f"Deployment blocked: {reason}")
```

## Next Steps

- 📖 Read full guide: [`docs/HARNESS_INTEGRATION.md`](docs/HARNESS_INTEGRATION.md)
- 🔄 Migration info: [`HARNESS_MIGRATION.md`](HARNESS_MIGRATION.md)
- 🧪 Run tests: `pytest tests/test_harness.py -v`
- 📊 View metrics: `python -m sdlc_agent.cli observe`

## Troubleshooting

**Q: Observability data not being written?**

A: Check configuration:
```python
harness = get_harness()
print(harness.config.enable_observability)  # Should be True
```

**Q: Hooks not firing?**

A: Register default hooks:
```python
from sdlc_agent import register_default_hooks
register_default_hooks(get_harness())
```

**Q: Coverage gate not working?**

A: Ensure coverage is set and hooks are registered:
```python
harness.state.coverage_pct = 85.0
harness._save_state()
```

## Support

Run the demo for a complete walkthrough:

```bash
python examples/harness_demo.py
```
