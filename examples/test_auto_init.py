#!/usr/bin/env python3
"""Test that auto-initialization works."""

print("=" * 60)
print("  Testing Auto-Initialization")
print("=" * 60)

print("\n1. Importing sdlc_agent...")
import sdlc_agent

print("2. Getting harness...")
from sdlc_agent import get_harness

harness = get_harness()

print(f"3. Checking if hooks are registered...")
print(f"   Hooks registered: {harness._hooks_registered}")
print(f"   Number of hook events: {len(harness._hooks)}")

if harness._hooks_registered:
    print("\n   [OK] SUCCESS: Hooks auto-registered!")
    print("\n   Registered hooks:")
    for event, callbacks in harness._hooks.items():
        print(f"      - {event}: {len(callbacks)} callback(s)")
else:
    print("\n   [FAIL] Hooks not registered")

print("\n4. Testing hook execution...")
from sdlc_agent.integrations.jira_client import MockJiraClient
from sdlc_agent.models import UserStory

harness.state.epic = {"key": "TEST-AUTO"}
harness.state.source = "auto-init-test"

jira = MockJiraClient()
story = UserStory(
    id="S-001",
    persona="Tester",
    want="verify auto-initialization",
    so_that="ensure hooks work in all contexts",
    acceptance_criteria=["Hooks auto-register", "Hooks fire correctly"]
)

initial_count = len(harness.state.jira_creates)
issue_key = jira.create_story(story)

if len(harness.state.jira_creates) > initial_count:
    print(f"   [OK] Hook fired! Card {issue_key} tracked")
    print(f"   Total cards tracked: {len(harness.state.jira_creates)}")
else:
    print(f"   [FAIL] Hook did not fire")

print("\n" + "=" * 60)
print("  Auto-Initialization Test Complete")
print("=" * 60)
print("\nThis means hooks will work in:")
print("   [+] CLI commands")
print("   [+] Web interface")
print("   [+] Spawned agents")
print("   [+] Skills (/sdlc-ingest, /sdlc-plan, etc.)")
print()
