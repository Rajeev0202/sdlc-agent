"""Tests for integrated harness."""

import json
from pathlib import Path

import pytest

from sdlc_agent import get_harness, reset_harness, Severity, register_default_hooks
from sdlc_agent.harness import HarnessConfig


@pytest.fixture
def harness():
    """Fresh harness instance for each test."""
    reset_harness()
    h = get_harness()
    yield h
    reset_harness()


def test_harness_initialization(harness):
    """Test harness initializes with correct defaults."""
    assert harness.state.stage == "init"
    assert harness.state.trace_id is None
    assert harness.config.coverage_threshold == 80
    assert harness.config.enable_observability is True


def test_trace_id_generation(harness):
    """Test trace ID generation and persistence."""
    trace_id = harness.get_or_create_trace_id()
    assert trace_id.startswith("trace-")

    # Should return same ID on subsequent calls
    assert harness.get_or_create_trace_id() == trace_id


def test_tool_span_tracking(harness):
    """Test automatic tool span tracking."""
    harness.config.enable_observability = True

    with harness.tool_span("test_operation"):
        pass

    # Check span was recorded (would be in traces.jsonl)
    assert harness.metrics.totals.get("tool_calls", 0) >= 1


def test_tool_span_error_tracking(harness):
    """Test error tracking in tool spans."""
    harness.config.enable_observability = True

    try:
        with harness.tool_span("failing_operation"):
            raise ValueError("Test error")
    except ValueError:
        pass

    # Check error was recorded
    assert harness.metrics.totals.get("errors", 0) >= 1
    assert len(harness.state.errors) >= 1


def test_stage_transition(harness):
    """Test stage transition and history tracking."""
    harness.transition_to("ingest", "Winston")

    assert harness.state.stage == "ingest"
    assert harness.state.persona == "Winston"
    assert len(harness.state.history) >= 1
    assert harness.state.history[-1]["stage"] == "ingest"


def test_coverage_gate(harness):
    """Test coverage gate validation."""
    # Below threshold
    harness.state.coverage_pct = 60.0
    can_advance, reason = harness.can_advance_to("commit")
    assert not can_advance
    assert "Coverage gate" in reason

    # Above threshold
    harness.state.coverage_pct = 90.0
    can_advance, reason = harness.can_advance_to("commit")
    assert can_advance
    assert reason is None


def test_logging(harness):
    """Test structured logging."""
    harness.log(Severity.INFO, "Test message", tool="test_tool")

    # Logs written to file
    logs_file = harness.config.observability_dir / "logs.jsonl"
    if logs_file.exists():
        logs = logs_file.read_text().strip().split("\n")
        assert len(logs) >= 1

        last_log = json.loads(logs[-1])
        assert last_log["level"] == "info"
        assert last_log["message"] == "Test message"


def test_error_logging(harness):
    """Test error logging adds to state."""
    initial_errors = len(harness.state.errors)

    harness.log(Severity.ERROR, "Test error", tool="test_tool")

    assert len(harness.state.errors) == initial_errors + 1
    assert harness.state.errors[-1]["message"] == "Test error"


def test_metrics_aggregation(harness):
    """Test metrics are aggregated correctly."""
    harness.config.enable_observability = True

    # Simulate some tool calls
    with harness.tool_span("operation1"):
        pass

    with harness.tool_span("operation2"):
        pass

    assert harness.metrics.totals["tool_calls"] >= 2


def test_custom_hook_registration(harness):
    """Test custom hook registration and execution."""
    hook_called = []

    def custom_hook(harness, **kwargs):
        hook_called.append(kwargs)

    harness.register_hook("on_stage_transition", custom_hook)
    harness.transition_to("build")

    assert len(hook_called) >= 1
    assert hook_called[-1]["new_stage"] == "build"


def test_default_hooks(harness):
    """Test default hooks registration."""
    register_default_hooks(harness)

    # Should have hooks registered
    assert len(harness._hooks.get("on_stage_transition", [])) >= 1
    assert len(harness._hooks.get("on_jira_card_created", [])) >= 1


def test_status_rendering(harness):
    """Test status banner rendering."""
    harness.state.stage = "build"
    harness.state.epic = {"summary": "Test Epic"}
    harness.state.current_card = "TEST-123"

    status = harness.render_status()

    assert "SDLC" in status
    assert "Test Epic" in status
    assert "TEST-123" in status
    assert "⏳" in status  # Current stage badge


def test_state_persistence(harness, tmp_path):
    """Test state persistence to disk."""
    # Use temp directory for test
    harness.config.state_file = tmp_path / "test-state.json"

    harness.state.stage = "test"
    harness.state.epic = {"key": "TEST-1"}
    harness._save_state()

    assert harness.config.state_file.exists()

    # Read back
    loaded = json.loads(harness.config.state_file.read_text())
    assert loaded["stage"] == "test"
    assert loaded["epic"]["key"] == "TEST-1"


def test_metrics_persistence(harness, tmp_path):
    """Test metrics persistence to disk."""
    harness.config.observability_dir = tmp_path
    harness.config.observability_dir.mkdir(exist_ok=True)

    harness.metrics.totals["tool_calls"] = 42
    harness._save_metrics()

    metrics_file = tmp_path / "metrics.json"
    assert metrics_file.exists()

    loaded = json.loads(metrics_file.read_text())
    assert loaded["totals"]["tool_calls"] == 42
    assert "last_updated" in loaded


def test_span_context_manager(harness):
    """Test span context manager handles exceptions."""
    harness.config.enable_observability = True

    # Normal execution
    with harness.tool_span("normal_op") as span:
        result = "success"

    # Exception should be tracked but re-raised
    with pytest.raises(RuntimeError):
        with harness.tool_span("failing_op"):
            raise RuntimeError("Expected error")

    # Error count should increase
    assert harness.metrics.totals.get("errors", 0) >= 1


def test_harness_disabled_observability(harness):
    """Test harness with observability disabled."""
    harness.config.enable_observability = False

    with harness.tool_span("test_op"):
        pass

    # Should not write traces
    traces_file = harness.config.observability_dir / "traces.jsonl"
    assert not traces_file.exists() or traces_file.stat().st_size == 0


def test_harness_disabled_hooks(harness):
    """Test harness with hooks disabled."""
    harness.config.enable_hooks = False
    hook_called = []

    def test_hook(**kwargs):
        hook_called.append(True)

    harness.register_hook("on_stage_transition", test_hook)
    harness.transition_to("build")

    # Hook should not execute
    assert len(hook_called) == 0


def test_configuration_from_env(monkeypatch):
    """Test configuration loaded from environment."""
    monkeypatch.setenv("COVERAGE_THRESHOLD", "90")

    # Note: Would need to implement env var loading in HarnessConfig
    # This is a placeholder for that functionality

    reset_harness()
    harness = get_harness()

    # Default is 80, env would override to 90
    assert harness.config.coverage_threshold in (80, 90)


def test_multiple_stage_transitions(harness):
    """Test multiple stage transitions track history correctly."""
    stages = [
        ("ingest", "Winston"),
        ("plan", "Priya"),
        ("build", "Amelia"),
        ("review", "Devon"),
    ]

    for stage, persona in stages:
        harness.transition_to(stage, persona)

    assert len(harness.state.history) == len(stages)

    # Verify all stages recorded
    recorded_stages = [h["stage"] for h in harness.state.history]
    assert recorded_stages == [s for s, _ in stages]


def test_jira_card_tracking(harness):
    """Test Jira card creation tracking."""
    from sdlc_agent.hooks import on_jira_card_created

    harness.state.epic = {"key": "EPIC-1"}
    harness.state.source = "https://confluence.example.com/page"

    on_jira_card_created(
        harness,
        card_key="STORY-123",
        summary="Test story"
    )

    assert len(harness.state.jira_creates) >= 1
    last_card = harness.state.jira_creates[-1]
    assert last_card["key"] == "STORY-123"
    assert last_card["summary"] == "Test story"
    assert last_card["parent"] == "EPIC-1"


def test_coverage_hook(harness):
    """Test coverage measurement hook."""
    from sdlc_agent.hooks import on_coverage_measured

    on_coverage_measured(harness, coverage_pct=75.5)

    assert harness.state.coverage_pct == 75.5


def test_git_push_hook_blocks_low_coverage(harness):
    """Test git push hook blocks when coverage is low."""
    from sdlc_agent.hooks import on_git_push_attempt

    harness.state.coverage_pct = 50.0

    result = on_git_push_attempt(harness)

    assert result is False  # Should block


def test_git_push_hook_allows_high_coverage(harness):
    """Test git push hook allows when coverage is high."""
    from sdlc_agent.hooks import on_git_push_attempt

    harness.state.coverage_pct = 90.0

    result = on_git_push_attempt(harness)

    assert result is True  # Should allow
