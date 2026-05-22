"""Quick manual test for Jira integration.

Run this to verify the Jira client works with your credentials.
"""
import os
from sdlc_agent.integrations import MockJiraClient, JiraClient
from sdlc_agent.models import UserStory

def test_mock_client():
    """Test the mock Jira client (no credentials needed)."""
    print("\n=== Testing MockJiraClient ===")
    mock = MockJiraClient(project_key="TEST")

    story = UserStory(
        id="S-001",
        persona="Developer",
        want="test the mock Jira client",
        so_that="I can verify it works without credentials",
        acceptance_criteria=[
            "Story is created in memory",
            "Issue key is returned",
            "Created issues are tracked"
        ],
        dependencies=[],
        risks=[]
    )

    issue_key = mock.create_story(story)
    print(f"[OK] Created mock issue: {issue_key}")
    print(f"[OK] Total issues created: {len(mock.created_issues)}")
    print(f"[OK] Issue details: {mock.created_issues[issue_key]['summary']}")
    return True

def test_real_client():
    """Test the real Jira client (requires environment variables)."""
    print("\n=== Testing Real JiraClient ===")

    # Check if credentials are configured
    required_vars = ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"]
    missing = [v for v in required_vars if not os.environ.get(v)]

    if missing:
        print(f"[SKIP] Missing environment variables: {', '.join(missing)}")
        print("\nTo test with real Jira, set these environment variables:")
        for var in required_vars:
            print(f"  {var}=<your-value>")
        print("\nSee JIRA_SETUP.md for detailed instructions.")
        return False

    try:
        client = JiraClient(
            server_url=os.environ["JIRA_URL"],
            email=os.environ["JIRA_EMAIL"],
            api_token=os.environ["JIRA_API_TOKEN"],
            project_key=os.environ["JIRA_PROJECT_KEY"]
        )

        story = UserStory(
            id="S-TEST",
            persona="QA Engineer",
            want="verify real Jira integration",
            so_that="I can confirm the API connection works",
            acceptance_criteria=[
                "Story is created in Jira Cloud",
                "All fields are populated correctly",
                "Issue key is returned"
            ],
            dependencies=["Jira API access"],
            risks=["API token might expire"]
        )

        print("Creating issue in Jira...")
        issue_key = client.create_story(story)
        print(f"[OK] Successfully created issue: {issue_key}")
        print(f"[OK] View it at: {os.environ['JIRA_URL']}/browse/{issue_key}")
        return True

    except Exception as e:
        print(f"[FAIL] Failed to create issue: {e}")
        print("\nCheck:")
        print("  1. Your credentials are correct")
        print("  2. The project key exists")
        print("  3. You have permission to create issues")
        return False

if __name__ == "__main__":
    print("SDLC Agent - Jira Integration Test")
    print("=" * 50)

    mock_ok = test_mock_client()
    real_ok = test_real_client()

    print("\n" + "=" * 50)
    if mock_ok and (real_ok or not all(os.environ.get(v) for v in ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"])):
        print("[OK] Jira integration is ready!")
    else:
        print("[WARN] Some tests failed - check the output above")
