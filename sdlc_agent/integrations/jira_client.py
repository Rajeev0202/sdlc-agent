"""Jira client — creates issues for the generated user stories using the JIRA Cloud REST API."""
from __future__ import annotations

import logging
from jira import JIRA
from ..models import UserStory

logger = logging.getLogger(__name__)


class MockJiraClient:
    """In-memory Jira client for testing and demo without credentials."""

    def __init__(self, project_key: str = "SCRUM") -> None:
        self.project_key = project_key
        self._issue_counter = 0
        self.created_issues: dict[str, dict] = {}

    def create_story(self, story: UserStory) -> str:
        """Create a mock JIRA issue for the given user story. Returns the issue key."""
        self._issue_counter += 1
        issue_key = f"{self.project_key}-{self._issue_counter}"
        self.created_issues[issue_key] = {
            'key': issue_key,
            'summary': story.want,
            'description': story.as_a_statement + "\n\nAcceptance Criteria:\n" + "\n".join(story.acceptance_criteria),
            'issuetype': 'Story',
            'story': story,
        }
        logger.info("Mock Jira: created issue %s for story %s", issue_key, story.id)
        return issue_key


class JiraClient:
    """Real Jira client using JIRA Cloud REST API."""

    def __init__(self, server_url: str, email: str, api_token: str, project_key: str = "SCRUM", auto_transition: str = None) -> None:
        self.server_url = server_url
        self.project_key = project_key
        self.auto_transition = auto_transition  # e.g., "Ready for QA"
        self.jira = JIRA(
            server=server_url,
            basic_auth=(email, api_token)
        )
        logger.info("Real Jira client initialized for %s (project: %s, auto_transition: %s)",
                    server_url, project_key, auto_transition)

    def create_story(self, story: UserStory) -> str:
        """Create a JIRA issue for the given user story. Returns the issue key."""
        issue_dict = {
            'project': {'key': self.project_key},
            'summary': story.want,
            'description': story.as_a_statement + "\n\nAcceptance Criteria:\n" + "\n".join(story.acceptance_criteria),
            'issuetype': {'name': 'Story'},
        }
        issue = self.jira.create_issue(fields=issue_dict)
        logger.info("Real Jira: created issue %s for story %s", issue.key, story.id)

        # Auto-transition to specified status if configured
        if self.auto_transition:
            try:
                self._transition_issue(issue, self.auto_transition)
            except Exception as e:
                logger.warning("Failed to transition %s to '%s': %s", issue.key, self.auto_transition, e)

        # Try to add to active sprint
        try:
            self._add_to_active_sprint(issue)
        except Exception as e:
            logger.warning("Failed to add %s to sprint: %s", issue.key, e)

        return issue.key

    def _transition_issue(self, issue, target_status: str) -> None:
        """Transition issue to target status."""
        transitions = self.jira.transitions(issue)

        # Find transition that leads to target status
        target_transition = None
        for t in transitions:
            if target_status.lower() in t['name'].lower() or target_status.lower() in t['to']['name'].lower():
                target_transition = t
                break

        if target_transition:
            self.jira.transition_issue(issue, target_transition['id'])
            logger.info("Transitioned %s to '%s'", issue.key, target_transition['to']['name'])
        else:
            available = [t['to']['name'] for t in transitions]
            logger.warning("No transition found for '%s'. Available: %s", target_status, available)

    def _add_to_active_sprint(self, issue) -> None:
        """Add issue to active sprint if one exists."""
        try:
            boards = self.jira.boards(projectKeyOrID=self.project_key)
            if not boards:
                return

            board = boards[0]
            sprints = self.jira.sprints(board.id, state='active')

            if sprints:
                sprint = sprints[0]
                self.jira.add_issues_to_sprint(sprint.id, [issue.key])
                logger.info("Added %s to sprint '%s'", issue.key, sprint.name)
        except Exception as e:
            logger.debug("Could not add to sprint: %s", e)
