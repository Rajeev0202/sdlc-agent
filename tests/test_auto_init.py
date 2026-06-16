"""Test automatic harness initialization."""

import sys
import importlib


def test_auto_init_on_import():
    """Test that hooks are auto-registered when module is imported."""
    # Fresh import
    if 'sdlc_agent' in sys.modules:
        # Force reload to test initialization
        importlib.reload(sys.modules['sdlc_agent'])
    else:
        import sdlc_agent

    from sdlc_agent import get_harness

    harness = get_harness()

    # Verify hooks are registered
    assert harness._hooks_registered, "Hooks should be auto-registered"
    assert "on_jira_card_created" in harness._hooks
    assert len(harness._hooks["on_jira_card_created"]) > 0
    assert "on_stage_transition" in harness._hooks
    assert len(harness._hooks["on_stage_transition"]) > 0


def test_hooks_work_after_auto_init():
    """Test that auto-registered hooks actually work."""
    from sdlc_agent import get_harness, reset_harness
    from sdlc_agent.integrations.jira_client import MockJiraClient
    from sdlc_agent.models import UserStory

    # Reset for clean test
    reset_harness()

    # Import should auto-initialize
    import sdlc_agent
    harness = get_harness()

    # Set up context
    harness.state.epic = {"key": "AUTO-TEST"}
    initial_count = len(harness.state.jira_creates)

    # Create Jira card
    jira = MockJiraClient()
    story = UserStory(
        id="S-001",
        persona="User",
        want="test auto-init",
        so_that="verify hooks work",
        acceptance_criteria=["Auto-initialization works"]
    )

    issue_key = jira.create_story(story)

    # Verify hook fired
    assert len(harness.state.jira_creates) == initial_count + 1
    assert harness.state.jira_creates[-1]["key"] == "SCRUM-1"


def test_ensure_harness_idempotent():
    """Test that ensure_harness can be called multiple times safely."""
    from sdlc_agent.bootstrap import ensure_harness

    h1 = ensure_harness()
    h2 = ensure_harness()
    h3 = ensure_harness()

    # Should all be the same instance
    assert h1 is h2
    assert h2 is h3

    # Hooks should only be registered once
    assert h1._hooks_registered


def test_orchestrator_auto_init():
    """Test that orchestrator automatically initializes harness."""
    from sdlc_agent import reset_harness
    from sdlc_agent.orchestrator import Orchestrator

    reset_harness()

    # Creating orchestrator should auto-init harness
    orchestrator = Orchestrator(use_harness=True)

    assert orchestrator.harness is not None
    assert orchestrator.harness._hooks_registered


def test_cli_import_auto_init():
    """Test that CLI import auto-initializes harness."""
    from sdlc_agent import reset_harness

    reset_harness()

    # Import CLI (should trigger auto-init)
    from sdlc_agent import cli

    from sdlc_agent import get_harness
    harness = get_harness()

    assert harness._hooks_registered


def test_stage_import_auto_init():
    """Test that stage import auto-initializes harness."""
    from sdlc_agent import reset_harness

    reset_harness()

    # Import stage (should trigger auto-init)
    from sdlc_agent.stages import stage2_stories

    from sdlc_agent import get_harness
    harness = get_harness()

    assert harness._hooks_registered
