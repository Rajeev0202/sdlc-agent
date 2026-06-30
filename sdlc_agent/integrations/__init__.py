"""Mocked external integrations.

Phase 1 deliberately keeps these in-memory so the orchestrator logic can be
exercised end-to-end without credentials. Swap any class for a real client
without changing the stage code — the stage modules only depend on the
public methods defined here.
"""
from .anthropic_client import ClaudeClient
from .confluence_client import ConfluenceClient, MockConfluenceClient, fetch_confluence_page
from .github_client import MockGitHubClient
from .github_rest_client import GitHubRestClient
from .git_operations import GitOperations
from .jira_client import MockJiraClient, JiraClient

__all__ = [
    "ClaudeClient",
    "ConfluenceClient",
    "MockConfluenceClient",
    "fetch_confluence_page",
    "MockGitHubClient",
    "GitHubRestClient",
    "GitOperations",
    "MockJiraClient",
    "JiraClient",
]
