#!/usr/bin/env python3
"""Demo: on_jira_card_created hook in action.

Run with: python examples/jira_hook_demo.py
"""

from sdlc_agent import get_harness, reset_harness, register_default_hooks, Severity
from sdlc_agent.integrations.jira_client import MockJiraClient
from sdlc_agent.models import UserStory


def demo_jira_hook():
    """Demonstrate the Jira card creation hook."""
    print("=" * 60)
    print("  Jira Card Creation Hook Demo")
    print("=" * 60)

    # 1. Setup harness
    reset_harness()
    harness = get_harness()
    register_default_hooks(harness)

    # Set up context
    harness.state.epic = {
        "key": "EPIC-123",
        "summary": "Card Freeze Feature"
    }
    harness.state.source = "https://confluence.example.com/page/123"
    harness.state.stage = "plan"

    print("\n📋 Initial State:")
    print(f"   Epic: {harness.state.epic['key']}")
    print(f"   Cards created so far: {len(harness.state.jira_creates)}")

    # 2. Add custom hook to demonstrate multiple hooks
    def notify_on_jira_create(harness, card_key, summary=None, **kwargs):
        print(f"\n📢 Custom Hook Fired!")
        print(f"   Card: {card_key}")
        print(f"   Summary: {summary}")
        print(f"   Stage: {harness.state.stage}")

    harness.register_hook("on_jira_card_created", notify_on_jira_create)

    # 3. Create Jira client and stories
    jira_client = MockJiraClient(project_key="DEMO")

    stories = [
        UserStory(
            id="S-001",
            persona="Customer",
            want="freeze their card via mobile app",
            so_that="they can prevent unauthorized transactions",
            acceptance_criteria=[
                "Customer can tap 'Freeze Card' button",
                "Card freezes within 5 seconds",
                "Frozen card rejects new transactions",
                "Customer receives confirmation notification"
            ]
        ),
        UserStory(
            id="S-002",
            persona="Customer",
            want="unfreeze their card instantly",
            so_that="they can resume normal transactions",
            acceptance_criteria=[
                "Customer can tap 'Unfreeze Card' button",
                "Card unfreezes within 5 seconds",
                "Unfrozen card accepts transactions",
                "Customer receives confirmation"
            ]
        ),
        UserStory(
            id="S-003",
            persona="Compliance Officer",
            want="audit all freeze/unfreeze events",
            so_that="regulatory requirements are met",
            acceptance_criteria=[
                "Every freeze event is logged with timestamp",
                "Every unfreeze event is logged",
                "Audit log is immutable",
                "Audit log includes user ID and reason"
            ]
        )
    ]

    print("\n" + "=" * 60)
    print("  Creating Jira Cards...")
    print("=" * 60)

    # 4. Create cards (hooks will fire for each)
    for i, story in enumerate(stories, 1):
        print(f"\n🔨 Creating card {i}/3...")
        issue_key = jira_client.create_story(story)

        print(f"   ✅ Created: {issue_key}")
        print(f"   Summary: {story.want}")

    # 5. Show final state
    print("\n" + "=" * 60)
    print("  Final State")
    print("=" * 60)

    print(f"\n📊 Total cards created: {len(harness.state.jira_creates)}")

    print("\n📝 Card History:")
    for create in harness.state.jira_creates:
        print(f"   • {create['key']}: {create['summary'][:50]}...")
        print(f"     Parent: {create['parent']}")
        print(f"     Time: {create['ts'][:19]}")

    # 6. Check observability
    print("\n📈 Observability:")
    logs_file = harness.config.observability_dir / "logs.jsonl"
    if logs_file.exists():
        import json
        logs = [json.loads(line) for line in logs_file.read_text().strip().split("\n") if line]
        jira_logs = [log for log in logs if "Jira card" in log.get("message", "")]
        print(f"   Log entries about Jira cards: {len(jira_logs)}")
        if jira_logs:
            print(f"   Latest: {jira_logs[-1]['message']}")
    else:
        print("   (No log file yet)")

    # 7. View state file
    print(f"\n💾 State saved to: {harness.config.state_file}")
    print(f"   View with: cat {harness.config.state_file}")

    print("\n" + "=" * 60)
    print("  Demo Complete!")
    print("=" * 60)
    print("\n💡 What happened:")
    print("   1. ✅ Default hook (on_jira_card_created) logged each card")
    print("   2. ✅ Custom hook printed notifications")
    print("   3. ✅ State file updated with audit trail")
    print("   4. ✅ Observability logs created")
    print("\n📖 See: docs/HARNESS_INTEGRATION.md for more details\n")


if __name__ == "__main__":
    demo_jira_hook()
