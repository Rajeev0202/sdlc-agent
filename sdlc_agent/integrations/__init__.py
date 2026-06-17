"""Mocked external integrations.

Phase 1 deliberately keeps these in-memory so the orchestrator logic can be
exercised end-to-end without credentials. Swap any class for a real client
without changing the stage code — the stage modules only depend on the
public methods defined here.
"""
from .anthropic_client import MockClaudeClient
from .confluence_client import MockConfluenceClient
from .github_client import MockGitHubClient
from .jira_client import MockJiraClient, JiraClient

__all__ = [
    "MockClaudeClient",
    "MockConfluenceClient",
    "MockGitHubClient",
    "MockJiraClient",
    "JiraClient",
]
