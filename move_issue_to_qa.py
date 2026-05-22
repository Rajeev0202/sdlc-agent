"""Move a Jira issue to Ready for QA status."""
import os
from jira import JIRA

# Connect to Jira
jira = JIRA(
    server=os.environ.get("JIRA_URL", "https://rrjha82.atlassian.net"),
    basic_auth=(
        os.environ.get("JIRA_EMAIL", "rrjha82@gmail.com"),
        os.environ.get("JIRA_API_TOKEN", "")
    )
)

issue_key = "SCRUM-19"

try:
    # Get the issue
    issue = jira.issue(issue_key)
    print(f"Issue: {issue_key}")
    print(f"Current status: {issue.fields.status.name}")
    print(f"Summary: {issue.fields.summary}")

    # Get available transitions
    print("\nAvailable transitions:")
    transitions = jira.transitions(issue)
    for t in transitions:
        print(f"  - {t['id']}: {t['name']} -> {t['to']['name']}")

    # Find "Ready for QA" transition
    qa_transition = None
    for t in transitions:
        if "qa" in t['name'].lower() or "qa" in t['to']['name'].lower():
            qa_transition = t
            break

    if qa_transition:
        print(f"\nTransitioning to: {qa_transition['to']['name']}")
        jira.transition_issue(issue, qa_transition['id'])

        # Refresh and confirm
        issue = jira.issue(issue_key)
        print(f"✓ Successfully moved to: {issue.fields.status.name}")
        print(f"✓ View at: {os.environ.get('JIRA_URL')}/browse/{issue_key}")
    else:
        print("\n⚠ No 'Ready for QA' transition found.")
        print("Available status transitions listed above.")
        print("\nTo move it manually:")
        print(f"1. Go to {os.environ.get('JIRA_URL')}/browse/{issue_key}")
        print("2. Click the status dropdown")
        print("3. Select 'Ready for QA'")

except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure JIRA_API_TOKEN environment variable is set.")
