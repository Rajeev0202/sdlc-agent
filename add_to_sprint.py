"""Add issue to active sprint."""
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
project_key = "SCRUM"

try:
    issue = jira.issue(issue_key)
    print(f"Issue: {issue_key} - {issue.fields.summary}")
    print(f"Status: {issue.fields.status.name}")

    # Get board ID for the project
    boards = jira.boards(projectKeyOrID=project_key)
    if not boards:
        print(f"\nNo boards found for project {project_key}")
        print(f"View issue directly at: {os.environ.get('JIRA_URL')}/browse/{issue_key}")
        exit(0)

    board = boards[0]
    print(f"\nBoard: {board.name} (ID: {board.id})")

    # Get active sprints
    sprints = jira.sprints(board.id, state='active')

    if sprints:
        sprint = sprints[0]
        print(f"Active sprint: {sprint.name} (ID: {sprint.id})")

        # Add issue to sprint
        jira.add_issues_to_sprint(sprint.id, [issue_key])
        print(f"[OK] Added {issue_key} to sprint: {sprint.name}")
        print(f"[OK] View board at: {os.environ.get('JIRA_URL')}/jira/software/projects/{project_key}/boards/{board.id}")
    else:
        print("\nNo active sprint found.")
        print("To see the issue on your board:")
        print(f"1. Go to {os.environ.get('JIRA_URL')}/jira/software/projects/{project_key}/boards/{board.id}/backlog")
        print(f"2. Find {issue_key} in the backlog")
        print("3. Drag it into an active sprint")
        print(f"\nOr view directly: {os.environ.get('JIRA_URL')}/browse/{issue_key}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
