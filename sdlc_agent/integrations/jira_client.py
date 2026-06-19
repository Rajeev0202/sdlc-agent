"""Jira client — creates issues for the generated user stories using the JIRA Cloud REST API."""
from __future__ import annotations

import logging
from jira import JIRA
from ..core.models import UserStory

logger = logging.getLogger(__name__)


def _trigger_jira_hook(card_key: str, summary: str | None = None):
    """Trigger the on_jira_card_created hook if harness is available."""
    try:
        from ..harness import get_harness
        harness = get_harness()
        harness._trigger_hook(
            "on_jira_card_created",
            card_key=card_key,
            summary=summary
        )
    except Exception:
        # Harness not available or hook failed - non-fatal
        pass


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

        # Trigger harness hook
        _trigger_jira_hook(card_key=issue_key, summary=story.want)

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
            'issuetype': {'name': 'Task'},  # Changed from 'Story' to 'Task' for broader compatibility
        }

        try:
            issue = self.jira.create_issue(fields=issue_dict)
            logger.info("Real Jira: created issue %s for story %s", issue.key, story.id)
        except Exception as e:
            # Log the full error details for debugging
            logger.error("Failed to create Jira issue for %s: %s", story.id, str(e))
            if hasattr(e, 'response'):
                logger.error("Response: %s", e.response.text if hasattr(e.response, 'text') else e.response)
            raise

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

        # Trigger harness hook
        _trigger_jira_hook(card_key=issue.key, summary=story.want)

        return issue.key

    def transition_to_status(self, issue_key: str, target_status: str, max_hops: int = 4) -> bool:
        """Transition an issue (by key) to the target status.

        Handles multi-step workflows automatically (e.g., To-Do -> In Progress -> Done).
        Returns True on success, False if no path found.
        """
        try:
            target_normalized = target_status.lower().replace(" ", "").replace("-", "")

            for hop in range(max_hops):
                issue = self.jira.issue(issue_key)
                current_status = issue.fields.status.name
                current_normalized = current_status.lower().replace(" ", "").replace("-", "")

                # Already at target?
                if current_normalized == target_normalized:
                    logger.info(f"{issue_key} reached '{target_status}' in {hop} hop(s)")
                    return True

                # Try direct transition first
                transitions = self.jira.transitions(issue)
                direct = self._find_transition(transitions, target_status)

                if direct:
                    self.jira.transition_issue(issue, direct['id'])
                    logger.info(f"{issue_key}: '{current_status}' -> '{direct['to']['name']}'")
                    continue

                # Find best intermediate step (prefer "In Progress" over "Blocked")
                preferred_order = ["in progress", "review", "ready"]
                intermediate = None
                for pref in preferred_order:
                    for t in transitions:
                        to_name = t['to']['name'].lower()
                        if pref in to_name:
                            intermediate = t
                            break
                    if intermediate:
                        break

                if not intermediate:
                    # Fallback: take any forward transition (skip "Blocked")
                    for t in transitions:
                        if "block" not in t['to']['name'].lower() and \
                           t['to']['name'].lower() != current_status.lower():
                            intermediate = t
                            break

                if not intermediate:
                    available = [t['to']['name'] for t in transitions]
                    logger.warning(f"{issue_key}: no forward transition. Available: {available}")
                    return False

                self.jira.transition_issue(issue, intermediate['id'])
                logger.info(f"{issue_key}: '{current_status}' -> '{intermediate['to']['name']}' (intermediate)")

            # Verify final status
            issue = self.jira.issue(issue_key)
            final_normalized = issue.fields.status.name.lower().replace(" ", "").replace("-", "")
            return final_normalized == target_normalized

        except Exception as e:
            logger.error("Failed to transition %s to %s: %s", issue_key, target_status, e)
            return False

    def _find_transition(self, transitions, target_status: str):
        """Find a transition that leads to target_status (case/space/hyphen-insensitive)."""
        target_normalized = target_status.lower().replace(" ", "").replace("-", "")
        for t in transitions:
            name_normalized = t['name'].lower().replace(" ", "").replace("-", "")
            to_normalized = t['to']['name'].lower().replace(" ", "").replace("-", "")
            if target_normalized == name_normalized or target_normalized == to_normalized:
                return t
        return None

    def _transition_issue(self, issue, target_status: str) -> None:
        """Transition issue to target status."""
        transitions = self.jira.transitions(issue)

        # Normalize target: remove spaces, hyphens, lowercase for fuzzy matching
        target_normalized = target_status.lower().replace(" ", "").replace("-", "")

        # Find transition that leads to target status
        target_transition = None
        for t in transitions:
            name_normalized = t['name'].lower().replace(" ", "").replace("-", "")
            to_normalized = t['to']['name'].lower().replace(" ", "").replace("-", "")
            if target_normalized == name_normalized or target_normalized == to_normalized:
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
