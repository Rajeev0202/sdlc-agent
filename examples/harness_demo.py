#!/usr/bin/env python3
"""Demo script showing integrated harness usage.

Run with: python examples/harness_demo.py
"""

import time
from pathlib import Path

from sdlc_agent import get_harness, register_default_hooks, Severity


def demo_basic_usage():
    """Demo: Basic harness usage"""
    print("\n=== Demo 1: Basic Harness Usage ===\n")

    harness = get_harness()
    register_default_hooks(harness)

    # Show initial state
    print(f"Current stage: {harness.state.stage}")
    print(f"Trace ID: {harness.get_or_create_trace_id()}")

    # Log messages
    harness.log(Severity.INFO, "Starting demo pipeline")
    harness.log(Severity.DEBUG, "Debug message - low priority")

    # Transition stages
    harness.transition_to("ingest", "Winston")
    print(f"\nTransitioned to: {harness.state.stage}")

    harness.transition_to("plan", "Priya")
    print(f"Transitioned to: {harness.state.stage}")

    # Show status
    print("\n" + harness.render_status())


def demo_tool_spans():
    """Demo: Automatic tool span tracking"""
    print("\n=== Demo 2: Tool Span Tracking ===\n")

    harness = get_harness()

    # Simulate tool execution with automatic tracking
    with harness.tool_span("read_brd", input_data="samples/brd_natwest.md"):
        print("Reading BRD...")
        time.sleep(0.1)  # Simulate work

    with harness.tool_span("parse_requirements"):
        print("Parsing requirements...")
        time.sleep(0.2)  # Simulate work

    # Simulate an error
    try:
        with harness.tool_span("validate_schema"):
            print("Validating schema...")
            raise ValueError("Invalid schema format")
    except ValueError:
        print("Error caught and logged to harness")

    # Show metrics
    print(f"\nTotal tool calls: {harness.metrics.totals.get('tool_calls', 0)}")
    print(f"Errors: {harness.metrics.totals.get('errors', 0)}")


def demo_custom_hooks():
    """Demo: Custom hook registration"""
    print("\n=== Demo 3: Custom Hooks ===\n")

    harness = get_harness()

    # Define custom hook
    def notify_slack(harness, old_stage, new_stage, **kwargs):
        print(f"📢 Slack notification: Pipeline moved {old_stage} → {new_stage}")

    def log_transition_time(harness, old_stage, new_stage, **kwargs):
        history = harness.state.history
        if len(history) >= 2:
            from datetime import datetime
            last = datetime.fromisoformat(history[-2]["ts"])
            current = datetime.fromisoformat(history[-1]["ts"])
            duration = (current - last).total_seconds()
            print(f"⏱️  Stage '{old_stage}' took {duration:.2f} seconds")

    # Register hooks
    harness.register_hook("on_stage_transition", notify_slack)
    harness.register_hook("on_stage_transition", log_transition_time)

    # Trigger transitions (hooks will fire)
    harness.transition_to("build", "Amelia")
    time.sleep(0.5)

    harness.transition_to("review", "Devon")
    time.sleep(0.3)

    harness.transition_to("deploy", "Marcus")


def demo_quality_gates():
    """Demo: Quality gates and validation"""
    print("\n=== Demo 4: Quality Gates ===\n")

    harness = get_harness()

    # Set coverage below threshold
    harness.state.coverage_pct = 65.0
    harness._save_state()

    can_advance, reason = harness.can_advance_to("commit")
    if not can_advance:
        print(f"❌ BLOCKED: {reason}")
    else:
        print("✅ Can advance to commit")

    # Increase coverage above threshold
    harness.state.coverage_pct = 85.0
    harness._save_state()

    can_advance, reason = harness.can_advance_to("commit")
    if not can_advance:
        print(f"❌ BLOCKED: {reason}")
    else:
        print("✅ Can advance to commit")


def demo_observability():
    """Demo: Observability data"""
    print("\n=== Demo 5: Observability ===\n")

    harness = get_harness()

    # Check observability files exist
    obs_dir = harness.config.observability_dir
    print(f"Observability directory: {obs_dir}")

    traces_file = obs_dir / "traces.jsonl"
    logs_file = obs_dir / "logs.jsonl"
    metrics_file = obs_dir / "metrics.json"

    if traces_file.exists():
        # Count trace entries
        with traces_file.open() as f:
            trace_count = sum(1 for _ in f)
        print(f"📊 Trace spans: {trace_count}")

    if logs_file.exists():
        # Count log entries
        with logs_file.open() as f:
            log_count = sum(1 for _ in f)
        print(f"📝 Log entries: {log_count}")

    if metrics_file.exists():
        print(f"📈 Metrics file: {metrics_file}")

        # Show metrics
        import json
        metrics = json.loads(metrics_file.read_text())
        print(f"   Total tool calls: {metrics['totals'].get('tool_calls', 0)}")
        print(f"   Error rate: {metrics['totals'].get('error_rate_pct', 0)}%")

        if metrics.get("by_stage"):
            print("\n   By Stage:")
            for stage, data in metrics["by_stage"].items():
                print(f"     {stage}: {data.get('runs', 0)} runs")

    print("\n💡 View full reports with: python -m sdlc_agent.cli observe")


def demo_state_persistence():
    """Demo: State persistence"""
    print("\n=== Demo 6: State Persistence ===\n")

    harness = get_harness()

    # Set some state
    harness.state.epic = {
        "key": "DEMO-123",
        "summary": "Harness Integration Demo"
    }
    harness.state.current_card = "DEMO-123"
    harness.state.branch = "feature/harness-demo"

    # Save
    harness._save_state()

    state_file = harness.config.state_file
    print(f"State saved to: {state_file}")

    # Read state
    import json
    state = json.loads(state_file.read_text())
    print(f"Epic: {state['epic']['summary']}")
    print(f"Card: {state['current_card']}")
    print(f"Branch: {state['branch']}")
    print(f"History entries: {len(state.get('history', []))}")


def main():
    """Run all demos"""
    print("=" * 60)
    print("  SDLC Agent - Integrated Harness Demo")
    print("=" * 60)

    from sdlc_agent import reset_harness

    # Reset for clean demo
    reset_harness()

    demos = [
        demo_basic_usage,
        demo_tool_spans,
        demo_custom_hooks,
        demo_quality_gates,
        demo_observability,
        demo_state_persistence,
    ]

    for demo in demos:
        try:
            demo()
            time.sleep(0.5)
        except Exception as e:
            print(f"\n⚠️  Demo error: {e}")

    print("\n" + "=" * 60)
    print("  Demo Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  • python -m sdlc_agent.cli status")
    print("  • python -m sdlc_agent.cli observe metrics")
    print("  • python -m sdlc_agent.cli observe traces")
    print("  • See docs/HARNESS_INTEGRATION.md for full guide")
    print()


if __name__ == "__main__":
    main()
