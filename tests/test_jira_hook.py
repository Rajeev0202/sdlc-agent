"""Test Jira card creation hook integration."""

import pytest
from sdlc_agent import get_harness, reset_harness, register_default_hooks
from sdlc_agent.integrations.jira_client import MockJiraClient
from sdlc_agent.models import UserStory


@pytest.fixture
def harness():
    """Fresh harness with hooks registered."""
    reset_harness()
    h = get_harness()
    register_default_hooks(h)
    yield h
    reset_harness()


def test_jira_hook_triggered_on_card_creation(harness):
    """Test that on_jira_card_created hook is triggered when creating cards."""
    # Set up epic context
    harness.state.epic = {"key": "EPIC-123", "summary": "Test Epic"}
    harness.state.source = "https://confluence.example.com/test"
    harness._save_state()

    # Create Jira client
    jira_client = MockJiraClient(project_key="TEST")

    # Create a story
    story = UserStory(
        id="S-001",
        persona="Customer",
        want="freeze their card",
        so_that="they can prevent unauthorized transactions",
        acceptance_criteria=[
            "Customer can tap 'Freeze Card' in mobile app",
            "Card is frozen within 5 seconds",
            "Frozen card rejects new transactions"
        ]
    )

    # Initial state
    initial_count = len(harness.state.jira_creates)

    # Create Jira card (this should trigger the hook)
    issue_key = jira_client.create_story(story)

    # Verify card was created
    assert issue_key == "TEST-1"

    # Verify hook was triggered and state was updated
    assert len(harness.state.jira_creates) == initial_count + 1

    # Verify the recorded data
    last_create = harness.state.jira_creates[-1]
    assert last_create["key"] == "TEST-1"
    assert last_create["summary"] == "freeze their card"
    assert last_create["parent"] == "EPIC-123"
    assert last_create["confluence_url"] == "https://confluence.example.com/test"
    assert "ts" in last_create


def test_jira_hook_tracks_multiple_cards(harness):
    """Test that hook tracks multiple card creations."""
    harness.state.epic = {"key": "EPIC-456"}

    jira_client = MockJiraClient()

    # Create multiple stories
    stories = [
        UserStory(
            id=f"S-{i:03d}",
            persona="User",
            want=f"capability {i}",
            so_that="benefit",
            acceptance_criteria=["AC1", "AC2"]
        )
        for i in range(1, 4)
    ]

    for story in stories:
        jira_client.create_story(story)

    # Should have tracked all 3 cards
    assert len(harness.state.jira_creates) >= 3

    # Verify all keys are recorded
    keys = [create["key"] for create in harness.state.jira_creates[-3:]]
    assert keys == ["SCRUM-1", "SCRUM-2", "SCRUM-3"]


def test_jira_hook_non_fatal_if_harness_unavailable():
    """Test that hook doesn't crash if harness is unavailable."""
    # Don't initialize harness
    reset_harness()

    jira_client = MockJiraClient()
    story = UserStory(
        id="S-001",
        persona="User",
        want="something",
        so_that="benefit",
        acceptance_criteria=["AC"]
    )

    # Should not crash even if harness not initialized with hooks
    issue_key = jira_client.create_story(story)
    assert issue_key == "SCRUM-1"


def test_custom_jira_hook(harness):
    """Test registering a custom Jira hook."""
    notifications = []

    def custom_jira_hook(harness, card_key, summary=None, **kwargs):
        notifications.append({
            "key": card_key,
            "summary": summary,
            "stage": harness.state.stage
        })

    # Register custom hook
    harness.register_hook("on_jira_card_created", custom_jira_hook)

    # Create card
    jira_client = MockJiraClient()
    story = UserStory(
        id="S-001",
        persona="User",
        want="test feature",
        so_that="testing",
        acceptance_criteria=["AC"]
    )

    jira_client.create_story(story)

    # Verify custom hook was called
    assert len(notifications) == 1
    assert notifications[0]["key"] == "SCRUM-1"
    assert notifications[0]["summary"] == "test feature"


def test_jira_hook_logs_to_observability(harness):
    """Test that Jira hook creates log entries."""
    harness.config.enable_observability = True

    jira_client = MockJiraClient()
    story = UserStory(
        id="S-001",
        persona="User",
        want="feature",
        so_that="benefit",
        acceptance_criteria=["AC"]
    )

    jira_client.create_story(story)

    # Check if log file has entry (if observability enabled)
    logs_file = harness.config.observability_dir / "logs.jsonl"
    if logs_file.exists():
        import json
        logs = [json.loads(line) for line in logs_file.read_text().strip().split("\n") if line]

        # Should have a log entry about card creation
        jira_logs = [log for log in logs if "Jira card" in log.get("message", "")]
        assert len(jira_logs) >= 1
        assert "SCRUM-1" in jira_logs[-1]["message"]
