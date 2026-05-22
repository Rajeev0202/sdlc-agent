# Jira Integration Setup

The SDLC Agent integrates with Jira to automatically create user story issues during Stage 2.

## Configuration

The integration supports two modes:

### 1. Mock Mode (Default)
No configuration needed. Stories are tracked in-memory for testing and demos.

### 2. Real Jira Mode
Set these environment variables to connect to your Jira Cloud instance:

```bash
# Windows PowerShell
$env:JIRA_URL="https://your-domain.atlassian.net"
$env:JIRA_EMAIL="your-email@example.com"
$env:JIRA_API_TOKEN="your-api-token"
$env:JIRA_PROJECT_KEY="SCRUM"
$env:JIRA_AUTO_STATUS="Ready for QA"  # Optional: auto-transition status

# Linux/Mac
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_PROJECT_KEY="SCRUM"
export JIRA_AUTO_STATUS="Ready for QA"  # Optional: auto-transition status
```

## Getting Your Jira API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label (e.g., "SDLC Agent")
4. Copy the token (you won't be able to see it again)

## How It Works

When Stage 2 runs (`stage2_stories.py`):
1. Checks if all four Jira environment variables are set
2. If yes: creates a `JiraClient` that calls the real Jira API
3. If no: falls back to `MockJiraClient` for in-memory tracking
4. For each generated user story, calls `create_story()`
5. The story is created in Jira with:
   - **Summary**: The "I want..." statement
   - **Description**: Full "As a... I want... so that..." + acceptance criteria
   - **Issue Type**: Story
   - **Project**: Your configured project key
6. **Automatically transitions** to status specified in `JIRA_AUTO_STATUS` (default: "Ready for QA")
7. **Automatically adds** to active sprint if one exists

## Verifying the Integration

Run a simple test:

```python
from sdlc_agent.integrations import JiraClient
from sdlc_agent.models import UserStory

# Create a test story
story = UserStory(
    id="TEST-001",
    persona="QA Engineer",
    want="verify Jira integration works",
    so_that="I can track stories automatically",
    acceptance_criteria=["Story is created in Jira", "Fields are populated correctly"],
    dependencies=[],
    risks=[]
)

# Initialize client (make sure env vars are set)
client = JiraClient(
    server_url="https://your-domain.atlassian.net",
    email="your-email@example.com",
    api_token="your-api-token",
    project_key="SCRUM"
)

# Create the story
issue_key = client.create_story(story)
print(f"Created issue: {issue_key}")
```

## Troubleshooting

### "JIRA API authentication error"
- Verify your email and API token are correct
- Check the token hasn't expired
- Ensure your account has permission to create issues

### "Project does not exist"
- Verify `JIRA_PROJECT_KEY` matches an existing project
- Check you have access to that project

### Falls back to mock mode unexpectedly
- Ensure ALL four environment variables are set
- Check for typos in variable names
- On Windows, use `$env:VAR_NAME`, not `$VAR_NAME`

## Security Notes

- **Never** commit API tokens to version control
- Use environment variables or a secure secrets manager
- Rotate tokens periodically
- Limit token scope to only required permissions
