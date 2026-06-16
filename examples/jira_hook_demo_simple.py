#!/usr/bin/env python3
"""Simple demo: on_jira_card_created hook in action."""

from sdlc_agent import get_harness, reset_harness, register_default_hooks
from sdlc_agent.integrations.jira_client import MockJiraClient
from sdlc_agent.models import UserStory


def main():
    print("=" * 60)
    print("  Jira Card Creation Hook Demo")
    print("=" * 60)

    # Setup harness with hooks
    reset_harness()
    harness = get_harness()
    register_default_hooks(harness)

    # Set context
    harness.state.epic = {"key": "EPIC-123", "summary": "Test Epic"}
    harness.state.source = "https://confluence.example.com/page"
    harness.state.stage = "plan"

    print("\nInitial State:")
    print(f"  Epic: {harness.state.epic['key']}")
    print(f"  Cards created: {len(harness.state.jira_creates)}")

    # Add custom hook
    def custom_hook(harness, card_key, summary=None, **kwargs):
        print(f"\n  -> Hook fired! Card: {card_key}")

    harness.register_hook("on_jira_card_created", custom_hook)

    # Create Jira cards
    jira = MockJiraClient(project_key="DEMO")

    stories = [
        UserStory(
            id="S-001",
            persona="Customer",
            want="freeze card",
            so_that="prevent fraud",
            acceptance_criteria=["Can tap freeze button", "Card freezes in 5s"]
        ),
        UserStory(
            id="S-002",
            persona="Customer",
            want="unfreeze card",
            so_that="resume transactions",
            acceptance_criteria=["Can tap unfreeze button", "Card unfreezes in 5s"]
        )
    ]

    print("\n" + "=" * 60)
    print("Creating Jira Cards...")
    print("=" * 60)

    for story in stories:
        issue_key = jira.create_story(story)
        print(f"\nCreated: {issue_key} - {story.want}")

    print("\n" + "=" * 60)
    print("Final State")
    print("=" * 60)

    print(f"\nTotal cards created: {len(harness.state.jira_creates)}")
    print("\nCard History:")
    for create in harness.state.jira_creates:
        print(f"  - {create['key']}: {create['summary']}")
        print(f"    Parent: {create['parent']}, Time: {create['ts'][:19]}")

    print(f"\nState file: {harness.config.state_file}")
    print("\nDone! Both default and custom hooks were called.")


if __name__ == "__main__":
    main()
